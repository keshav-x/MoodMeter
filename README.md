# MoodMeter

Natural language processing tool and web dashboard for analyzing customer reviews. It scores sentiment polarity, detects department themes, flags urgent safety hazards, and routes issues to the right team.

Built to run 100% self-contained with zero server dependencies on Vercel and zero paid subscriptions.

---

## Key Features

- Continuous Polarity Scoring: Scores review text from -1.0 (very negative) to +1.0 (very positive) with negation and intensifier support.
- Department Categorization: Flags themes across 6 operational areas: Product Quality, App & Software, Customer Service, Shipping & Delivery, Pricing & Billing, and Safety & Health.
- Safety Hazard Interception: Instantly catches critical defect words (fire, smoke, shock, burn, overheat, exploded) and triggers immediate high-priority routing.
- Dual-Mode Architecture: Runs locally on a Python Flask backend (http://127.0.0.1:5000), or as a zero-server Edge app on Vercel using client-side JavaScript.
- Clean Earth Palette: Styled in a high-contrast executive theme (rust, amber, forest green, charcoal on warm ivory).

---

## System Architecture

```
+-----------------------------------------------+
|              Customer Review Text             |
|        (Web form, CSV upload, or API)         |
+-----------------------------------------------+
                       |
                       v
+-----------------------------------------------+
|           1. Safety Hazard Check              |
|   Keywords: fire, smoke, overheat, burn, shock|
+-----------------------------------------------+
       |                                 |
 (Hazard Found)                    (No Hazard)
       |                                 |
       v                                 v
+----------------------+     +-----------------------+
| Urgent Priority (P1) |     | 2. Sentiment Scoring  |
| Route directly to:   |     | Polarity: -1.0 to +1.0|
| Legal & Safety Team  |     +-----------------------+
+----------------------+                 |
                                         v
                             +-----------------------+
                             | 3. Department Match   |
                             | App, Hardware, Support|
                             +-----------------------+
                                         |
                                         v
                             +-----------------------+
                             | 4. Standard Routing   |
                             | Normal Priority (P2)  |
                             +-----------------------+
```

### How the Pipeline Works

1. Review Ingestion:
   Accepts text input from single submissions, bulk CSV file uploads, or JSON REST API requests.

2. Safety Hazard Scan:
   Scans text for critical safety words (such as fire, smoke, burn, overheat, shock). If detected, it bypasses regular queues, tags the review as Urgent (P1), and assigns it to Legal and Safety Compliance.

3. Sentiment Scoring:
   Evaluates sentiment on a scale from -1.0 to +1.0:
   - Positive: Polarity >= +0.10
   - Neutral: -0.10 < Polarity < +0.10
   - Negative: Polarity <= -0.10

4. Department Categorization:
   Matches keywords against 6 operational teams:
   - Safety & Health: Overheating, smoke, physical defects
   - Product Quality: Hardware durability, build finish, audio quality
   - App & Software: App crashes, Bluetooth dropouts, sync errors
   - Customer Service: Support response times, agent helpfulness
   - Shipping & Delivery: Transit delays, damaged packaging
   - Pricing & Billing: Subscriptions, unexpected charges, refunds

5. Dual-Mode Execution:
   - Local Mode: Uses app.py with Flask and TextBlob for server-side processing.
   - Vercel Serverless Mode: Uses an embedded client-side JavaScript engine inside static/engine.js. All scoring runs in the browser in under 1ms with zero backend server required.

---

## Local Setup & Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/keshav-x/MoodMeter.git
cd MoodMeter
```

### 2. (Optional) Create Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
python -m textblob.download_corpora
```

### 4. Run the Local Server
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser.

---

## How to Deploy on Vercel (Zero Server Needed)

MoodMeter runs on Vercel without needing any backend server, subscription, or container:

1. Push or fork this repository to your GitHub account.
2. Log in to Vercel (https://vercel.com) and click "Add New Project".
3. Import the MoodMeter repository.
4. Leave build settings as default (Framework Preset: Other, Build Command: empty, Output Directory: ./).
5. Click "Deploy".

Vercel serves index.html and static files directly from its global Edge network.

---

## REST API Specification (When Running Locally)

### 1. Analyse Single or Batch Reviews
- Endpoint: POST /api/analyse
- Payload:
  ```json
  {
    "review": {
      "text": "The charger got burning hot and emitted smoke overnight.",
      "product": "SmartWatch X1"
    }
  }
  ```
- Response:
  ```json
  {
    "count": 1,
    "results": [
      {
        "product": "SmartWatch X1",
        "sentiment": {
          "label": "Negative",
          "polarity": -0.38
        },
        "themes": ["Safety & Health"],
        "urgency": {
          "is_urgent": true,
          "explanation": "Flagged as urgent: safety/health triggers detected."
        },
        "suggested_team": "Legal and Safety Compliance",
        "triage_explanation": "Flagged: safety hazard detected. Immediate routing to Legal and Safety Compliance."
      }
    ]
  }
  ```

### 2. Feedback Feed & Summary
- GET /api/reviews: List analysed reviews with optional query filters (?sentiment=negative, ?urgent=true).
- GET /api/summary: Aggregate distribution metrics across sentiment, urgency, and topic themes.

---

## Project Structure

```
MoodMeter/
├── index.html                  # Standalone Vercel Edge frontend
├── vercel.json                 # Vercel deployment configuration
├── app.py                      # Flask REST API and NLP pipeline
├── requirements.txt            # Minimal dependencies (Flask, TextBlob)
├── README.md                   # Project documentation
├── static/
│   ├── style.css               # Executive Earth design system (CSS)
│   └── engine.js               # Client-side triage and NLP engine (JS)
└── sample_data/
    ├── sample_reviews.json     # Curated test reviews
    └── sample_reviews.csv      # CSV batch intake sample
```

---

## Author

Developed by Keshav Chaudhary (https://github.com/keshav-x).
