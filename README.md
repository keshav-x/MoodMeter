# MoodMeter: Brand Sentiment Intelligence and Automated Triage Platform

An explainable, lexicon-based Natural Language Processing (NLP) system and web console for ingesting unstructured customer feedback, evaluating sentiment polarity, detecting operational themes, and flagging critical safety hazards for departmental triage.

Developed as a Summer Industrial Training project in **Python & Artificial Intelligence** at **Grziti Interactive** (5 June - 19 July 2026), affiliated with **Rayat Bahra Institute of Engineering & Nanotechnology, Hoshiarpur**.

---

## 1. Project Overview & Core Purpose

Modern consumer hardware and digital platforms receive thousands of unstructured reviews, app store ratings, and support tickets daily. In this firehose of text:
1. **Critical Safety Hazards** (e.g. overheating batteries, charging cable sparks, medical allergic reactions) get buried under ordinary inquiries.
2. **Product Defect Trends** (e.g. repeated bluetooth sync crashes after a firmware update) take days or weeks to reach mobile engineering teams.
3. **Black-Box AI Models** frequently fail compliance audits because they cannot explain *why* a customer message was flagged or routed.

**MoodMeter** solves this by providing a lightweight, transparent, rule-based triage pipeline. Every decision is explainable, mathematically auditable, and backed by a plain-English rationale.

---

## 2. Zero-Subscription Architecture (100% Free & Self-Contained)

> **Important**: MoodMeter does NOT require any paid API keys (no OpenAI, no Anthropic, no AWS Bedrock) and does NOT require any cloud database subscriptions.

### How MoodMeter Handles Everything Locally
- **Local Lexicon Engine**: MoodMeter uses `TextBlob`'s underlying PatternTagger sentiment dictionary (`en-sentiment.xml`), containing ~2,900 annotated English adjectives with pre-assigned polarity and subjectivity scores.
- **Zero API Dependency**: All tokenization, negation detection, and score scaling execute directly on your local CPU in standard Python.
- **Deterministic Triage Dictionaries**: Topic themes (Quality, Software, Shipping, Billing, Safety) are matched using curated high-speed keyword dictionaries.
- **Local Web Server & API**: Powered by a lightweight Flask WSGI application that runs on `http://127.0.0.1:5000` with an in-memory data store.
- **Total Operational Cost**: **$0.00**. Completely functional offline without an internet connection.

---

## 3. System Architecture & NLP Pipeline

The analysis pipeline processes each review through six deterministic stages:

```
[Customer Feedback]
         │
         ▼
1. Preprocessing & Normalisation (lowercase, strip noise, tokenise)
         │
         ▼
2. Lexicon Polarity Scoring (TextBlob heuristic: -1.00 to +1.00)
         │
         ▼
3. Topic Theme Categorisation (6 operational dictionary scans)
         │
         ▼
4. Urgency & Hazard Evaluation (Safety trigger check + negative polarity)
         │
         ▼
5. Departmental Triage Suggestion (Legal, Engineering, CX, Finance)
         │
         ▼
6. Human-in-the-Loop Safeguard Flag (Mandatory audit tag attached)
```

### Sentiment Scoring Rules
- **Continuous Polarity**: Ranging from `-1.00` (maximally negative) to `+1.00` (maximally positive).
- **Negation Inversion**: Modifiers like "not", "never", "hardly" invert base polarity (e.g., "not great" scales positive score to negative).
- **Intensity Modifiers**: Degree adverbs ("very", "extremely", "slightly") scale score magnitude.
- **Classification Thresholds**:
  - `Positive`: Polarity > `+0.10`
  - `Neutral`: Polarity between `-0.10` and `+0.10`
  - `Negative`: Polarity < `-0.10`

### Urgency & Safety Hazard Criteria
A review is flagged as **Urgent Escalation** if:
1. It contains one or more catastrophic hazard trigger phrases: `fire`, `smoke`, `shock`, `burn`, `overheat`, `exploded`, `allergic reaction`, `hospital`, `injury`.
2. **AND** the computed sentiment polarity is `< 0.00`.
3. If flagged, the ticket is immediately marked `Escalate Immediately` and routed to **Legal and Safety Compliance**.

---

## 4. Quick Start: Local Installation & Execution

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.14 installed.
- Git installed.

### Setup Instructions

```bash
# 1. Navigate to the project directory
cd A:\projects\internship\MoodMeter

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scriptsctivate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download local NLP corpora (one-time setup)
python -m textblob.download_corpora

# 5. Start the web application
python app.py
```

Open your browser to: **`http://127.0.0.1:5000`**

On startup, MoodMeter automatically loads a curated 5-review test corpus demonstrating all core classification outcomes.

---

## 5. Web Console & 1-Click Examiner Demo Scenarios

The web interface is styled in Microsoft's **Prismatic Polygons** theme (warm ivory canvas, deep midnight plum serif headings, coral/rose accents, clean cards, no emojis, no em-dashes).

To demonstrate the system during your viva examination in under 60 seconds, use the three 1-click test buttons at the top of the tester:

| Scenario | Button | Input Preview | Expected Outcome |
|---|---|---|---|
| **Scenario 1** | `[Praise Example]` | "The audio clarity and active noise cancellation are superb. Battery lasted 14 hours..." | **Positive** (+0.65) &bull; Standard Priority &bull; Routed to Customer Experience |
| **Scenario 2** | `[Complaint Example]` | "The mobile app refuses to sync step counts and crashes on bluetooth settings..." | **Negative** (-0.42) &bull; Standard Priority &bull; Routed to Mobile & Web Engineering |
| **Scenario 3** | `[Safety Hazard Alert]` | "Safety alert: the charging port got burning hot and emitted a burning smell..." | **Urgent Safety Flag** (-0.38) &bull; Escalate Immediately &bull; Routed to Legal & Safety |

---

## 6. REST API Specification

MoodMeter exposes a complete RESTful JSON interface for external integrations:

### 1. Analyse Single or Batch Reviews
- **Endpoint**: `POST /api/analyse`
- **Headers**: `Content-Type: application/json`

**Sample Request**:
```bash
curl -X POST http://127.0.0.1:5000/api/analyse   -H "Content-Type: application/json"   -d '{"review": {"text": "Battery pack started smoking while charging overnight.", "product": "SmartWatch X1"}}'
```

**Sample Response**:
```json
{
  "count": 1,
  "results": [
    {
      "review_id": "a1b2c3d4",
      "product": "SmartWatch X1",
      "sentiment": {
        "label": "Negative",
        "polarity": -0.35,
        "subjectivity": 0.60,
        "method": "TextBlob pattern-based polarity (lexicon heuristic)"
      },
      "themes": ["Safety & Health"],
      "urgency": {
        "is_urgent": true,
        "matched_triggers": ["smoking"],
        "explanation": "Flagged as urgent due to safety hazard keywords."
      },
      "suggested_team": "Legal and Safety Compliance",
      "triage_explanation": "Sentiment: Negative (polarity=-0.35). | Detected themes: Safety & Health. | Urgent safety hazard detected. | Suggested routing: Legal and Safety Compliance.",
      "requires_human_review": true
    }
  ]
}
```

### 2. Retrieve Feedback Feed
- **Endpoint**: `GET /api/reviews`
- **Query Parameters**:
  - `?sentiment=positive` | `?sentiment=negative` | `?sentiment=neutral`
  - `?urgent=true`
  - `?product=SmartWatch X1`

### 3. Aggregate Summary Statistics
- **Endpoint**: `GET /api/summary`
- **Response**: Returns total reviews, sentiment breakdown, urgent count, and topic theme distribution.

---

## 7. Project Structure

```
MoodMeter/
├── app.py                      # Core Flask application, NLP pipeline, and routing
├── requirements.txt            # Minimal dependencies (Flask, TextBlob)
├── README.md                   # Complete architectural documentation
├── sample_data/
│   ├── sample_reviews.json     # 5 curated test reviews across key scenarios
│   └── sample_reviews.csv      # CSV format for batch upload demonstration
├── static/                     # Static styling assets
└── templates/
    └── dashboard.html          # Prismatic Polygons web console with examiner presets
```

---

## 8. Limitations & Engineering Disclosures

1. **Sarcasm Detection**: Like all lexicon heuristics, statements containing sarcastic praise (e.g. *"Great, another bug after update"*) may be scored positive due to the token *"Great"*.
2. **Context Specificity**: Medical and hardware jargon may occasionally fall outside general English lexicons.
3. **Governance Safeguard**: All automated classifications output `"requires_human_review": true` to mandate human oversight for compliance.
