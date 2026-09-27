"""
Core NLP and Triage Engine for MoodMeter.
Provides modular components for sentiment polarity analysis,
safety hazard detection, multi-label theme classification, and team routing.
"""

from dataclasses import dataclass, field
from textblob import TextBlob

# safety hazard trigger keywords that require immediate escalation
SAFETY_TRIGGERS = [
    "fire", "smoke", "spark", "burn", "shock", "exploded", "explosion",
    "melted", "burning", "hospital", "injury", "bleeding", "hazard",
    "flame", "flames", "shocked", "overheat", "overheated", "overheating",
    "caught fire"
]

# theme keyword dictionaries for operational departments
THEME_KEYWORDS = {
    "Product Quality": [
        "quality", "durability", "material", "build", "broken", "broke",
        "sturdy", "cheap", "flimsy", "defect", "defective", "hardware",
        "battery", "sound", "screen", "finish", "craftsmanship",
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
        "overheat", "overheated", "hazard", "flame", "flames", "shocked",
    ],
}

# team routing lookup table
TEAM_MAP = {
    "Product Quality": "Hardware Engineering",
    "Customer Service": "Support Operations",
    "Shipping & Delivery": "Logistics & Fulfillment",
    "Pricing & Billing": "Finance & Billing",
    "App & Software": "Mobile & QA Engineering",
    "General Feedback": "Product Management",
}


@dataclass
class SentimentResult:
    polarity: float
    subjectivity: float
    label: str


@dataclass
class TriageResult:
    is_urgent: bool
    urgency_explanation: str
    suggested_team: str
    triage_explanation: str


class SentimentAnalyzer:
    """Calculates continuous polarity and subjectivity using TextBlob."""

    @staticmethod
    def analyze(text: str) -> SentimentResult:
        # added sentiment logic using textblob polarity
        blob = TextBlob(text)
        polarity = round(blob.sentiment.polarity, 4)
        subjectivity = round(blob.sentiment.subjectivity, 4)

        if polarity >= 0.10:
            label = "Positive"
        elif polarity <= -0.10:
            label = "Negative"
        else:
            label = "Neutral"

        return SentimentResult(polarity=polarity, subjectivity=subjectivity, label=label)


class HazardDetector:
    """Checks review text for severe safety hazard triggers."""

    @staticmethod
    def contains_hazard(text: str) -> bool:
        # check for critical safety hazard keywords
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in SAFETY_TRIGGERS)


class ThemeClassifier:
    """Categorizes text into operational department themes."""

    @staticmethod
    def classify(text: str) -> list[str]:
        # identify operational themes based on keywords
        text_lower = text.lower()
        matched = []
        for theme, keywords in THEME_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(theme)
        return matched if matched else ["General Feedback"]


class TriageRouter:
    """Evaluates urgency priority and determines team routing."""

    @staticmethod
    def route(polarity: float, label: str, themes: list[str], text: str) -> TriageResult:
        text_lower = text.lower()
        has_hazard = HazardDetector.contains_hazard(text_lower)
        has_safety_theme = "Safety & Health" in themes

        # route safety hazards to legal and compliance immediately
        if has_hazard or has_safety_theme:
            return TriageResult(
                is_urgent=True,
                urgency_explanation="Flagged as urgent: safety/health triggers detected.",
                suggested_team="Legal and Safety Compliance",
                triage_explanation="Flagged: safety hazard detected. Immediate routing to Legal and Safety Compliance."
            )

        # route serious software bugs to engineering
        if "App & Software" in themes and (polarity <= -0.50 or "crash" in text_lower):
            return TriageResult(
                is_urgent=True,
                urgency_explanation="Flagged as urgent: severe software malfunction reported.",
                suggested_team="Mobile & QA Engineering",
                triage_explanation="Urgent bug report: customer reports crash/severe malfunction. Route to Mobile & QA Engineering."
            )

        # route severe negative feedback for quick recovery
        if polarity <= -0.65:
            return TriageResult(
                is_urgent=True,
                urgency_explanation="Flagged as urgent: severe customer dissatisfaction (polarity <= -0.65).",
                suggested_team="Customer Support (Escalations)",
                triage_explanation="Critical dissatisfaction: immediate outreach recommended to prevent churn."
            )

        # default routing based on matched theme
        primary_theme = themes[0] if themes else "General Feedback"
        suggested_team = TEAM_MAP.get(primary_theme, "Product Management")

        if label == "Negative":
            explanation = f"Assigned to {suggested_team} for review and follow-up."
        elif label == "Positive":
            explanation = f"Routed to {suggested_team} as positive customer feedback."
        else:
            explanation = f"Logged for {suggested_team} monitoring."

        return TriageResult(
            is_urgent=False,
            urgency_explanation="Standard priority.",
            suggested_team=suggested_team,
            triage_explanation=explanation
        )


def process_review(text: str, product: str = "Unknown", source: str = "Web Form", review_id: str = None) -> dict:
    """Full pipeline to score and triage a single review text."""
    sent = SentimentAnalyzer.analyze(text)
    themes = ThemeClassifier.classify(text)
    triage = TriageRouter.route(sent.polarity, sent.label, themes, text)

    return {
        "id": review_id or "REV-001",
        "text": text,
        "product": product,
        "source": source,
        "sentiment": {
            "polarity": sent.polarity,
            "subjectivity": sent.subjectivity,
            "label": sent.label,
        },
        "themes": themes,
        "urgency": {
            "is_urgent": triage.is_urgent,
            "explanation": triage.urgency_explanation,
        },
        "suggested_team": triage.suggested_team,
        "triage_explanation": triage.triage_explanation,
    }
