# MoodMeter

A simple tool to analyze customer reviews, detect whether feedback is positive or negative, catch urgent safety issues (like overheating or fire risks), and send each ticket to the right department.

Runs locally with Python and Flask, or directly on Vercel as a zero-server static site.

---

## Features

- Sentiment scoring from -1.0 (very negative) to +1.0 (very positive).
- Auto-routes to 6 departments: Product Quality, App & Software, Customer Service, Shipping, Billing, and Safety & Health.
- Safety hazard alerts: Catches dangerous words like fire, smoke, burn, or overheat and flags them as urgent immediately.
- Works without a backend on Vercel using client-side JavaScript.
- Clean, minimal earth tone interface.

---

## Architecture & How It Works

Here is the simple flow of how each review moves through the system:

```
Incoming Review (Web Form, CSV Upload, or API)
      |
      v
Check for Safety Hazards (fire, smoke, overheat, shock)
      |-- Found Hazard -> Mark as URGENT (P1) and route to Legal & Safety team
      |-- No Hazard    -> Continue to sentiment analysis
      v
Score Sentiment with TextBlob (-1.0 to +1.0)
      v
Match Department by Keywords (Hardware, Mobile QA, Support, Logistics, Billing)
      v
Output Result to Dashboard / API Response
```

### Breakdown of the Pipeline

1. Safety Check First: If a customer reports something burning, smoking, or sparking, we bypass normal queues right away. The review gets tagged as urgent and routed straight to Legal & Safety Compliance.
2. Sentiment Analysis: Uses TextBlob to score polarity from -1.0 to +1.0. Scores of 0.1 or higher are positive, -0.1 or lower are negative, and the rest are neutral.
3. Department Matching: Looks for keywords to figure out which team should take action (for example, app crashes go to Mobile QA, transit delays go to Logistics).
4. Dual-Mode Setup:
   - Local: Runs via app.py using Flask and TextBlob at http://127.0.0.1:5000.
   - Vercel: Runs entirely inside the browser using JavaScript (static/engine.js). It requires zero backend hosting or server configuration.

---

## Running Locally

### 1. Clone the repo
```bash
git clone https://github.com/keshav-x/MoodMeter.git
cd MoodMeter
```

### 2. Set up virtual environment (optional)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install requirements
```bash
pip install -r requirements.txt
python -m textblob.download_corpora
```

### 4. Start the app
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser.

---


## API Endpoints (Local Flask)

### Analyze a Review
- POST /api/analyse
- Body:
  ```json
  {
    "review": {
      "text": "The charger got burning hot and started smoking.",
      "product": "SmartWatch X1"
    }
  }
  ```
- Returns the polarity score, department tag, urgency flag, and assigned team.

### Get Stored Reviews & Summary
- GET /api/reviews: Returns list of processed reviews (supports ?sentiment=negative or ?urgent=true).
- GET /api/summary: Returns breakdown of sentiment counts, urgency percentage, and top topics.

---

## Project Structure

```
MoodMeter/
├── index.html                  # Main dashboard page
├── vercel.json                 # Vercel static hosting config
├── app.py                      # Flask backend and NLP logic
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation
├── static/
│   ├── style.css               # Dashboard styling
│   └── engine.js               # Client-side analysis engine for Vercel
└── sample_data/
    ├── sample_reviews.json     # Test reviews
    └── sample_reviews.csv      # Test CSV batch
```

---

## Author

Keshav Chaudhary (https://github.com/keshav-x)
