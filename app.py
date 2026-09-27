"""
MoodMeter — Brand Sentiment Intelligence Platform
===================================================
A local Flask application that analyses customer reviews for brand sentiment,
identifies complaint themes, flags urgent cases, and suggests team routing.

Technical approach
------------------
Sentiment classification uses TextBlob's pattern-based polarity scorer.
TextBlob computes polarity (−1 to +1) from a lexicon of ~2 900 adjectives
with pre-assigned polarity scores, applying modifiers for negation, intensity,
and sentence structure.  This is *not* a trained ML model — it is a transparent,
rule-based heuristic.  It works well for informal customer reviews but can miss
sarcasm, domain jargon, and nuanced language.

Theme detection uses keyword matching against a curated dictionary of common
complaint categories.  Urgency flagging combines negative polarity with a set
of trigger phrases (safety, legal, refund, health, threat keywords).

Limitations
-----------
* Sentiment accuracy is limited by TextBlob's general-purpose lexicon.
* Theme detection relies on keyword lists, not a trained topic model.
* Urgency rules are heuristic — they may under- or over-flag edge cases.
* All processing is local; no external API calls are made.
"""

import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from textblob import TextBlob
import pandas as pd

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder=".")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# In-memory store for analysed reviews (reset on restart)
_review_store: list[dict] = []

# ---------------------------------------------------------------------------
# NLP helpers
# ---------------------------------------------------------------------------

# Theme keyword dictionary — each key is a theme label, values are trigger words.
THEME_KEYWORDS: dict[str, list[str]] = {
    "Product Quality": [
        "broken", "defective", "damaged", "cracked", "stopped working",
        "malfunction", "poor quality", "cheaply made", "fell apart",
    ],
    "Customer Service": [
        "customer service", "support", "disconnected", "unhelpful", "rude",
        "no response", "ignored", "waiting for response", "hold",
    ],
    "Shipping & Delivery": [
        "shipping", "delivery", "late", "delayed", "lost package",
        "wrong item", "tracking", "never arrived",
    ],
    "Pricing & Billing": [
        "price", "expensive", "overpriced", "billing", "charged",
        "subscription", "refund", "overcharged", "price increase",
    ],
    "App & Software": [
        "app", "crash", "bug", "update", "sync", "slow", "glitch",
        "error", "software", "login",
    ],
    "Safety & Health": [
        "safety", "hazard", "allergic", "burn", "hot", "injury",
        "health", "dangerous", "toxic", "hurt",
    ],
}

# Urgency trigger phrases — presence combined with negative sentiment → urgent.
URGENCY_TRIGGERS: list[str] = [
    "refund", "legal", "lawyer", "consumer protection", "sue",
    "safety", "hazard", "injury", "hurt", "allergic", "health",
    "dangerous", "unacceptable", "immediately", "asap", "now",
    "someone gets hurt", "contact authorities",
]

# Team routing map — maps primary detected theme to a suggested team.
TEAM_ROUTING: dict[str, str] = {
    "Product Quality": "Quality Assurance",
    "Customer Service": "Customer Experience",
    "Shipping & Delivery": "Logistics & Fulfilment",
    "Pricing & Billing": "Billing & Finance",
    "App & Software": "Engineering / Dev-Ops",
    "Safety & Health": "Legal & Compliance (URGENT)",
}


def analyse_sentiment(text: str) -> dict:
    """Return polarity, subjectivity, and a human-readable label."""
    blob = TextBlob(text)
    polarity = round(blob.sentiment.polarity, 4)
    subjectivity = round(blob.sentiment.subjectivity, 4)

    if polarity > 0.1:
        label = "Positive"
    elif polarity < -0.1:
        label = "Negative"
    else:
        label = "Neutral"

    return {
        "polarity": polarity,
        "subjectivity": subjectivity,
        "label": label,
        "method": "TextBlob pattern-based polarity (lexicon heuristic)",
    }


def detect_themes(text: str) -> list[str]:
    """Match review text against keyword dictionary; return theme labels."""
    lower = text.lower()
    matched = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            matched.append(theme)
    return matched if matched else ["General Feedback"]


SAFETY_TRIGGERS: list[str] = [
    "safety", "hazard", "injury", "hurt", "allergic", "health",
    "dangerous", "toxic", "someone gets hurt",
    "fire", "smoke", "burn", "burning", "overheat", "overheating",
    "exploded", "explosion", "spark", "shock",
]


def check_urgency(text: str, polarity: float) -> dict:
    """Flag urgent reviews using trigger phrases combined with polarity.

    Safety/health triggers flag as urgent regardless of polarity because
    TextBlob can assign positive polarity to polite safety reports.
    Other urgency triggers require negative polarity (< -0.05).
    """
    lower = text.lower()
    matched_triggers = [t for t in URGENCY_TRIGGERS if t in lower]
    matched_safety = [t for t in SAFETY_TRIGGERS if t in lower]

    # Safety triggers are always urgent; others need negative polarity
    is_urgent = (
        len(matched_safety) > 0
        or (polarity < -0.05 and len(matched_triggers) > 0)
    )

    if is_urgent and matched_safety:
        explanation = (
            f"Flagged as urgent: safety/health triggers {matched_safety} detected "
            f"(polarity={polarity:.2f}). Safety triggers override polarity threshold."
        )
    elif is_urgent:
        explanation = (
            f"Flagged as urgent: negative polarity ({polarity:.2f}) combined "
            f"with trigger phrases {matched_triggers}."
        )
    else:
        explanation = "Not flagged as urgent."

    return {
        "is_urgent": is_urgent,
        "matched_triggers": matched_triggers,
        "explanation": explanation,
    }


def suggest_team(themes: list[str], urgency: dict) -> str:
    """Suggest a team based on the primary theme and urgency."""
    if urgency["is_urgent"] and "Safety & Health" in themes:
        return TEAM_ROUTING["Safety & Health"]
    for theme in themes:
        if theme in TEAM_ROUTING:
            return TEAM_ROUTING[theme]
    return "General Support"


def build_triage_explanation(sentiment: dict, themes: list[str],
                             urgency: dict, team: str) -> str:
    """Build a transparent, audit-friendly explanation of the triage decision."""
    parts = [
        f"Sentiment: {sentiment['label']} (polarity={sentiment['polarity']}, "
        f"subjectivity={sentiment['subjectivity']}). "
        f"Method: {sentiment['method']}.",
        f"Detected themes: {', '.join(themes)}.",
        urgency["explanation"],
        f"Suggested routing: {team}.",
        "This decision is based on keyword matching and polarity scoring. "
        "A human reviewer should verify before taking action.",
    ]
    return " | ".join(parts)


def analyse_review(review: dict) -> dict:
    """Full analysis pipeline for a single review."""
    text = review.get("text", "")
    if not text or not text.strip():
        return {
            "error": "Review text is empty.",
            "original": review,
        }

    sentiment = analyse_sentiment(text)
    themes = detect_themes(text)
    urgency = check_urgency(text, sentiment["polarity"])
    team = suggest_team(themes, urgency)
    explanation = build_triage_explanation(sentiment, themes, urgency, team)

    result = {
        "review_id": review.get("id", str(uuid.uuid4())[:8]),
        "source": review.get("source", "Unknown"),
        "product": review.get("product", "Unknown"),
        "date": review.get("date", ""),
        "text": text,
        "sentiment": sentiment,
        "themes": themes,
        "urgency": urgency,
        "suggested_team": team,
        "triage_explanation": explanation,
        "requires_human_review": True,  # Always flag for human review
        "analysed_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    return result


# ---------------------------------------------------------------------------
# Routes — Web dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    """Render the main dashboard page."""
    return render_template("index.html", reviews=_review_store)


@app.route("/upload", methods=["POST"])
def upload():
    """Handle single review or CSV batch upload from the web form."""
    # Single review
    review_text = request.form.get("review_text", "").strip()
    source = request.form.get("source", "Web Form")
    product = request.form.get("product", "Unknown")

    results = []

    if review_text:
        review = {
            "id": f"WEB-{len(_review_store)+1:04d}",
            "text": review_text,
            "source": source,
            "product": product,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
        }
        result = analyse_review(review)
        _review_store.append(result)
        results.append(result)

    # CSV file
    csv_file = request.files.get("csv_file")
    if csv_file and csv_file.filename:
        try:
            stream = io.StringIO(csv_file.stream.read().decode("utf-8"))
            reader = csv.DictReader(stream)
            for row in reader:
                result = analyse_review(row)
                _review_store.append(result)
                results.append(result)
        except Exception as e:
            return render_template("index.html", reviews=_review_store,
                                   error=f"CSV parse error: {e}")

    return render_template("index.html", reviews=_review_store,
                           latest_count=len(results))


# ---------------------------------------------------------------------------
# Routes — JSON API
# ---------------------------------------------------------------------------

@app.route("/api/analyse", methods=["POST"])
def api_analyse():
    """Analyse one or more reviews via JSON API.

    Accepts:
        {"review": {"text": "...", ...}}
      or
        {"reviews": [{"text": "...", ...}, ...]}

    Returns:
        {"results": [...], "count": N}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    reviews = []
    if "review" in data:
        reviews.append(data["review"])
    elif "reviews" in data:
        reviews = data["reviews"]
    else:
        return jsonify({"error": "Provide 'review' or 'reviews' key."}), 400

    if not reviews:
        return jsonify({"error": "No reviews provided."}), 400

    results = []
    for rev in reviews:
        if not isinstance(rev, dict) or "text" not in rev:
            results.append({"error": "Each review must be an object with a 'text' field.", "input": rev})
            continue
        result = analyse_review(rev)
        _review_store.append(result)
        results.append(result)

    return jsonify({"results": results, "count": len(results)})


@app.route("/api/reviews", methods=["GET"])
def api_reviews():
    """Return all analysed reviews, optionally filtered by sentiment or urgency."""
    sentiment_filter = request.args.get("sentiment", "").lower()
    urgent_only = request.args.get("urgent", "").lower() == "true"
    product_filter = request.args.get("product", "").lower()

    filtered = _review_store
    if sentiment_filter:
        filtered = [r for r in filtered if r.get("sentiment", {}).get("label", "").lower() == sentiment_filter]
    if urgent_only:
        filtered = [r for r in filtered if r.get("urgency", {}).get("is_urgent")]
    if product_filter:
        filtered = [r for r in filtered if r.get("product", "").lower() == product_filter]

    return jsonify({"reviews": filtered, "count": len(filtered), "total": len(_review_store)})


@app.route("/api/summary", methods=["GET"])
def api_summary():
    """Return aggregate sentiment summary across all stored reviews."""
    if not _review_store:
        return jsonify({"message": "No reviews analysed yet."})

    total = len(_review_store)
    pos = sum(1 for r in _review_store if r.get("sentiment", {}).get("label") == "Positive")
    neg = sum(1 for r in _review_store if r.get("sentiment", {}).get("label") == "Negative")
    neu = sum(1 for r in _review_store if r.get("sentiment", {}).get("label") == "Neutral")
    urgent = sum(1 for r in _review_store if r.get("urgency", {}).get("is_urgent"))

    avg_polarity = sum(r.get("sentiment", {}).get("polarity", 0) for r in _review_store) / total

    # Theme distribution
    theme_counts: dict[str, int] = {}
    for r in _review_store:
        for t in r.get("themes", []):
            theme_counts[t] = theme_counts.get(t, 0) + 1

    # Product breakdown
    product_sentiment: dict[str, dict] = {}
    for r in _review_store:
        prod = r.get("product", "Unknown")
        if prod not in product_sentiment:
            product_sentiment[prod] = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
        label = r.get("sentiment", {}).get("label", "Neutral")
        product_sentiment[prod][label.lower()] += 1
        product_sentiment[prod]["total"] += 1

    return jsonify({
        "total_reviews": total,
        "sentiment_distribution": {"positive": pos, "negative": neg, "neutral": neu},
        "average_polarity": round(avg_polarity, 4),
        "urgent_count": urgent,
        "theme_distribution": theme_counts,
        "product_breakdown": product_sentiment,
    })


@app.route("/api/health", methods=["GET"])
def api_health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "reviews_stored": len(_review_store)})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Load sample data on startup for demonstration
    sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "sample_reviews.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            samples = json.load(f)
        for s in samples:
            _review_store.append(analyse_review(s))
        print(f"Loaded {len(samples)} sample reviews from {sample_path}")

    print("MoodMeter starting at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
