"""
MoodMeter: Brand Sentiment Intelligence Platform
Local Flask application that analyses customer reviews for brand sentiment,
identifies complaint themes, flags urgent cases, and suggests team routing.
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

# setup flask app and static folder
app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder=".")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# in-memory store for analysed reviews
_review_store: list[dict] = []

# safety hazard trigger keywords that require immediate escalation
SAFETY_TRIGGERS = [
    "fire", "smoke", "spark", "burn", "shock", "exploded", "explosion",
    "melted", "burning", "hospital", "injury", "bleeding", "hazard",
    "flame", "flames", "shocked", "overheat", "overheated", "overheating",
    "caught fire"
]


# check for critical safety hazard keywords
def check_safety_hazard(text: str) -> bool:
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in SAFETY_TRIGGERS)


# added sentiment logic using textblob polarity
def get_sentiment(text: str) -> dict:
    blob = TextBlob(text)
    polarity = round(blob.sentiment.polarity, 4)
    subjectivity = round(blob.sentiment.subjectivity, 4)

    if polarity >= 0.10:
        label = "Positive"
    elif polarity <= -0.10:
        label = "Negative"
    else:
        label = "Neutral"

    return {
        "polarity": polarity,
        "subjectivity": subjectivity,
        "label": label,
    }


# theme keywords for department categorization
THEME_KEYWORDS = {
    "Product Quality": [
        "quality", "durability", "material", "build", "broken", "broke",
        "sturdy", "cheap", "flimsy", "defect", "defective", "hardware",
        "battery", "sound", "screen", "finish", "craftsmanship", "craft",
    ],
    "Customer Service": [
        "support", "service", "representative", "agent", "call", "chat",
        "helpful", "rude", "unresponsive", "wait", "hold", "email",
        "response", "ticket", "polite", "courteous", "attitude",
    ],
    "Shipping & Delivery": [
        "shipping", "delivery", "arrived", "late", "fast", "package",
        "damaged", "box", "carrier", "tracking", "courier", "dispatch",
        "delay", "transit", "on time",
    ],
    "Pricing & Billing": [
        "price", "cost", "expensive", "cheap", "refund", "charge",
        "billing", "subscription", "worth", "value", "overpriced",
        "fee", "renewal", "discount",
    ],
    "App & Software": [
        "app", "software", "bug", "crash", "freeze", "slow", "update",
        "sync", "login", "connection", "bluetooth", "interface", "ui",
        "glitch", "error", "disconnect",
    ],
    "Safety & Health": [
        "fire", "smoke", "spark", "burn", "shock", "injury", "toxic",
        "harm", "danger", "exploded", "melted", "burning", "hospital",
        "overheat", "overheated", "hazard", "flame", "flames", "shocked"
    ],
}


# identify operational themes based on keywords
def get_themes(text: str) -> list[str]:
    text_lower = text.lower()
    matched = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(theme)
    return matched if matched else ["General Feedback"]


# triage logic: determine urgency and routing team
def triage_review(polarity: float, label: str, themes: list[str],
                  text: str) -> tuple[bool, str, str, str]:
    text_lower = text.lower()
    has_safety_theme = "Safety & Health" in themes
    has_safety_kw = check_safety_hazard(text_lower)

    # route safety hazards to legal and compliance immediately
    if has_safety_kw or has_safety_theme:
        return (
            True,
            "Flagged as urgent: safety/health triggers detected.",
            "Legal and Safety Compliance",
            "Flagged: safety hazard detected. Immediate routing to Legal and Safety Compliance."
        )

    # route serious software bugs to engineering
    if "App & Software" in themes and (polarity <= -0.50 or "crash" in text_lower):
        return (
            True,
            "Flagged as urgent: severe software malfunction reported.",
            "Mobile & QA Engineering",
            "Urgent bug report: customer reports crash/severe malfunction. Route to Mobile & QA Engineering."
        )

    # route severe negative feedback for quick recovery
    if polarity <= -0.65:
        return (
            True,
            "Flagged as urgent: severe customer dissatisfaction (polarity <= -0.65).",
            "Customer Support (Escalations)",
            "Critical dissatisfaction: immediate outreach recommended to prevent churn."
        )

    # default routing based on matched theme
    team_map = {
        "Product Quality": "Hardware Engineering",
        "Customer Service": "Support Operations",
        "Shipping & Delivery": "Logistics & Fulfillment",
        "Pricing & Billing": "Finance & Billing",
        "App & Software": "Mobile & QA Engineering",
        "General Feedback": "Product Management",
    }
    primary_theme = themes[0] if themes else "General Feedback"
    suggested_team = team_map.get(primary_theme, "Product Management")

    if label == "Negative":
        explanation = f"Assigned to {suggested_team} for review and follow-up."
    elif label == "Positive":
        explanation = f"Routed to {suggested_team} as positive customer feedback."
    else:
        explanation = f"Logged for {suggested_team} monitoring."

    return False, "Standard priority.", suggested_team, explanation


# run full analysis pipeline on a review record
def analyse_review(review: dict) -> dict:
    text = review.get("text", "")
    sentiment = get_sentiment(text)
    themes = get_themes(text)
    is_urgent, urgency_exp, team, triage_exp = triage_review(
        sentiment["polarity"], sentiment["label"], themes, text
    )

    return {
        "id": review.get("id", str(uuid.uuid4())[:8]),
        "text": text,
        "source": review.get("source", "Unknown"),
        "product": review.get("product", "Unknown"),
        "date": review.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "sentiment": sentiment,
        "themes": themes,
        "urgency": {
            "is_urgent": is_urgent,
            "explanation": urgency_exp,
        },
        "suggested_team": team,
        "triage_explanation": triage_exp,
    }


# load sample review data from json file
def load_sample_data(filepath: str) -> None:
    global _review_store
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        result = analyse_review(item)
        _review_store.append(result)
    print(f"Loaded {len(_review_store)} sample reviews from {filepath}")


# web dashboard route
@app.route("/")
def dashboard():
    return render_template("index.html")


# handle single review or csv file upload
@app.route("/upload", methods=["POST"])
def upload():
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
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        result = analyse_review(review)
        _review_store.append(result)
        results.append(result)

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
            return jsonify({"error": f"CSV parse error: {e}"}), 400

    return render_template("index.html")


# api endpoint: analyse reviews via post
@app.route("/api/analyse", methods=["POST"])
def api_analyse():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    results = []
    if "review" in data:
        result = analyse_review(data["review"])
        _review_store.append(result)
        results.append(result)
    elif "reviews" in data and isinstance(data["reviews"], list):
        for r in data["reviews"]:
            result = analyse_review(r)
            _review_store.append(result)
            results.append(result)
    else:
        return jsonify({"error": "Payload must contain 'review' or 'reviews' key"}), 400

    return jsonify({"count": len(results), "results": results}), 200


# api endpoint: retrieve all analysed reviews with optional filters
@app.route("/api/reviews", methods=["GET"])
def api_reviews():
    sentiment_filter = request.args.get("sentiment")
    urgent_filter = request.args.get("urgent")
    product_filter = request.args.get("product")
    limit = request.args.get("limit", default=None, type=int)

    filtered = _review_store

    if sentiment_filter:
        filtered = [r for r in filtered
                    if r["sentiment"]["label"].lower() == sentiment_filter.lower()]

    if urgent_filter is not None:
        is_urg = urgent_filter.lower() in ("true", "1", "yes")
        filtered = [r for r in filtered if r["urgency"]["is_urgent"] == is_urg]

    if product_filter:
        filtered = [r for r in filtered
                    if product_filter.lower() in r["product"].lower()]

    if limit:
        filtered = filtered[:limit]

    return jsonify({"total": len(filtered), "reviews": filtered}), 200


# api endpoint: summary metrics and theme breakdown
@app.route("/api/summary", methods=["GET"])
def api_summary():
    total = len(_review_store)
    if total == 0:
        return jsonify({
            "total_reviews": 0,
            "sentiment_distribution": {"Positive": 0, "Neutral": 0, "Negative": 0},
            "urgency_count": 0,
            "top_themes": [],
            "mean_polarity": 0.0,
        }), 200

    labels = [r["sentiment"]["label"] for r in _review_store]
    polarities = [r["sentiment"]["polarity"] for r in _review_store]
    urgent_count = sum(1 for r in _review_store if r["urgency"]["is_urgent"])

    theme_counts: dict[str, int] = {}
    for r in _review_store:
        for t in r["themes"]:
            theme_counts[t] = theme_counts.get(t, 0) + 1

    sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)

    return jsonify({
        "total_reviews": total,
        "sentiment_distribution": {
            "Positive": labels.count("Positive"),
            "Neutral": labels.count("Neutral"),
            "Negative": labels.count("Negative"),
        },
        "urgency_count": urgent_count,
        "urgency_percentage": round((urgent_count / total) * 100, 1),
        "mean_polarity": round(sum(polarities) / total, 4),
        "top_themes": [{"theme": t, "count": c} for t, c in sorted_themes],
    }), 200


# start local development server
if __name__ == "__main__":
    sample_path = os.path.join(
        os.path.dirname(__file__), "sample_data", "sample_reviews.json"
    )
    load_sample_data(sample_path)
    print("MoodMeter starting at http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
