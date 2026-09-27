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
from triage_engine import process_review

# setup flask app and static folder
app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder=".")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# in-memory store for analysed reviews
_review_store: list[dict] = []


def analyse_review(review: dict) -> dict:
    """Wrapper that enriches review record with date and id."""
    text = review.get("text", "")
    product = review.get("product", "Unknown")
    source = review.get("source", "Web Form")
    review_id = review.get("id", str(uuid.uuid4())[:8])

    res = process_review(text=text, product=product, source=source, review_id=review_id)
    res["date"] = review.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    return res


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
        filtered = [r for r in filtered if r["sentiment"]["label"].lower() == sentiment_filter.lower()]

    if urgent_filter is not None:
        is_urg = urgent_filter.lower() in ("true", "1", "yes")
        filtered = [r for r in filtered if r["urgency"]["is_urgent"] == is_urg]

    if product_filter:
        filtered = [r for r in filtered if product_filter.lower() in r["product"].lower()]

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
    sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "sample_reviews.json")
    load_sample_data(sample_path)
    print("MoodMeter starting at http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
