// client-side sentiment analysis and triage engine for Vercel
const EXAMPLES = {
    positive: { text: "The audio clarity and active noise cancellation are superb. Battery lasted through an entire 14-hour flight. Highly recommend!", product: "AudioMax Pro" },
    praise: { text: "The audio clarity and active noise cancellation are superb. Battery lasted through an entire 14-hour flight. Highly recommend!", product: "AudioMax Pro" },
    negative: { text: "The mobile app refuses to sync step count and crashes every time I open Bluetooth settings. Very frustrating bug.", product: "FitBand Plus" },
    complaint: { text: "The mobile app refuses to sync step count and crashes every time I open Bluetooth settings. Very frustrating bug.", product: "FitBand Plus" },
    safety: { text: "Safety alert: the charging port got burning hot and emitted smoke overnight while plugged into the wall adapter!", product: "SmartWatch X1" },
    hazard: { text: "Safety alert: the charging port got burning hot and emitted smoke overnight while plugged into the wall adapter!", product: "SmartWatch X1" }
};

// exactly 1 verified review for each type: Positive, Bug/Negative, Safety Hazard, Neutral Inquiry
const INITIAL_REVIEWS = [
    {
        id: "REV-001",
        product: "AudioMax Pro",
        date: "2026-06-15",
        text: "The audio clarity and active noise cancellation are superb. Battery lasted through an entire 14-hour flight. Highly recommend!",
        sentiment: { label: "Positive", polarity: 0.65 },
        themes: ["Product Quality"],
        urgency: { is_urgent: false, explanation: "Standard priority." },
        suggested_team: "Hardware Engineering",
        triage_explanation: "Routed to Hardware Engineering as positive customer feedback."
    },
    {
        id: "REV-002",
        product: "FitBand Plus",
        date: "2026-06-18",
        text: "The mobile app refuses to sync step count and crashes every time I open Bluetooth settings. Very frustrating bug.",
        sentiment: { label: "Negative", polarity: -0.55 },
        themes: ["App & Software"],
        urgency: { is_urgent: true, explanation: "Flagged as urgent: severe software malfunction reported." },
        suggested_team: "Mobile & QA Engineering",
        triage_explanation: "Urgent bug report: customer reports crash/severe malfunction."
    },
    {
        id: "REV-003",
        product: "SmartWatch X1",
        date: "2026-06-22",
        text: "Safety alert: the charging port got burning hot and emitted smoke overnight while plugged into the wall adapter!",
        sentiment: { label: "Negative", polarity: -0.45 },
        themes: ["Safety & Health"],
        urgency: { is_urgent: true, explanation: "Flagged as urgent: safety/health triggers detected." },
        suggested_team: "Legal and Safety Compliance",
        triage_explanation: "Flagged: safety hazard detected. Immediate routing to Legal and Safety Compliance."
    },
    {
        id: "REV-004",
        product: "SmartWatch X1",
        date: "2026-06-28",
        text: "Can I connect these headphones to two devices simultaneously via multipoint bluetooth? Please clarify battery specs.",
        sentiment: { label: "Neutral", polarity: 0.05 },
        themes: ["General Feedback"],
        urgency: { is_urgent: false, explanation: "Standard priority." },
        suggested_team: "Customer Support",
        triage_explanation: "Logged for Customer Support monitoring."
    }
];

const LEXICON = {
    superb: 0.9, clarity: 0.8, recommend: 0.8, great: 0.8, good: 0.6, excellent: 0.9, love: 0.8, outstanding: 0.9,
    bad: -0.6, terrible: -0.9, worst: -0.9, poor: -0.7, broken: -0.8, defect: -0.8, frustrating: -0.7, bug: -0.6,
    crash: -0.8, crashes: -0.8, smoke: -0.7, burning: -0.7, fire: -0.8, late: -0.5, refuse: -0.6, refuses: -0.6
};

const HAZARDS = ["fire", "smoke", "spark", "burn", "burning", "shock", "exploded", "melted", "overheat", "overheated"];
const THEMES = {
    "Safety & Health": ["fire", "smoke", "spark", "burn", "burning", "shock", "hazard", "overheat", "exploded"],
    "Product Quality": ["quality", "clarity", "sound", "battery", "build", "broken", "durability", "hardware"],
    "App & Software": ["app", "software", "crash", "crashes", "bug", "bluetooth", "sync", "freeze"],
    "Shipping & Delivery": ["shipping", "delivery", "late", "package", "box", "damaged"],
    "Customer Service": ["support", "service", "agent", "rep", "ticket", "refund", "inquiry"]
};

let allReviews = [...INITIAL_REVIEWS];
let currentFilter = "all";

// fill example text into the form
window.fillExample = function(type) {
    const ex = EXAMPLES[type];
    if (!ex) return;
    const textEl = document.getElementById("reviewText");
    const prodEl = document.getElementById("productName");
    if (textEl) textEl.value = ex.text;
    if (prodEl) prodEl.value = ex.product;
};

// client-side sentiment analysis and triage logic for Vercel
window.evaluateClientSideNLP = function(text, product) {
    const lower = text.toLowerCase();
    const words = lower.replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter(Boolean);
    let total = 0, count = 0;
    words.forEach(w => {
        if (LEXICON[w] !== undefined) {
            total += LEXICON[w];
            count++;
        }
    });

    const polarity = count > 0 ? parseFloat((total / count).toFixed(2)) : 0.0;
    const label = polarity >= 0.1 ? "Positive" : (polarity <= -0.1 ? "Negative" : "Neutral");

    const matchedThemes = [];
    for (const [theme, kws] of Object.entries(THEMES)) {
        if (kws.some(k => lower.includes(k))) matchedThemes.push(theme);
    }
    if (!matchedThemes.length) matchedThemes.push("General Feedback");

    const hasHazard = HAZARDS.some(k => lower.includes(k));
    const isUrgent = hasHazard || (matchedThemes.includes("App & Software") && (polarity <= -0.5 || lower.includes("crash")));

    let team = "Product Management";
    let explanation = "Logged for standard review.";
    if (hasHazard) {
        team = "Legal and Safety Compliance";
        explanation = "Flagged: safety hazard detected. Immediate routing to Legal and Safety Compliance.";
    } else if (matchedThemes.includes("App & Software") && isUrgent) {
        team = "Mobile & QA Engineering";
        explanation = "Urgent bug report: customer reports crash/malfunction.";
    } else if (matchedThemes.includes("Shipping & Delivery")) {
        team = "Logistics & Fulfillment";
        explanation = "Assigned to Logistics & Fulfillment.";
    } else if (matchedThemes.includes("Product Quality")) {
        team = "Hardware Engineering";
        explanation = "Assigned to Hardware Engineering.";
    }

    return {
        id: "VERCEL-" + Date.now().toString().slice(-4),
        product: product || "General Product",
        date: new Date().toISOString().slice(0, 10),
        text: text,
        sentiment: { label, polarity },
        themes: matchedThemes,
        urgency: {
            is_urgent: isUrgent,
            explanation: isUrgent ? "Flagged as urgent priority." : "Standard priority."
        },
        suggested_team: team,
        triage_explanation: explanation
    };
};

// handle review analysis form submission
window.handleAnalyse = async function(event) {
    if (event) event.preventDefault();

    const textEl = document.getElementById("reviewText");
    const prodEl = document.getElementById("productName");
    if (!textEl) return;

    const text = textEl.value.trim();
    const product = prodEl ? prodEl.value.trim() || "General Product" : "General Product";
    if (!text) return;

    let item = null;

    // try local Flask API first
    try {
        const res = await fetch("/api/analyse", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ review: { text, product } })
        });
        if (res.ok) {
            const data = await res.json();
            item = data.results ? data.results[0] : data.result;
        }
    } catch (_) {}

    // fallback to client-side NLP on Vercel
    if (!item) {
        item = window.evaluateClientSideNLP(text, product);
    }

    // prepend to verified feed so it shows up immediately at the top
    allReviews.unshift(item);
    updateSummaryCounters();
    renderFeed();

    // display classification result box
    const box = document.getElementById("resultBox");
    if (box) {
        box.style.display = "block";

        const isUrgent = item.urgency?.is_urgent;
        const sent = item.sentiment?.label || "Neutral";
        const badge = document.getElementById("resultBadge");
        if (badge) {
            badge.className = "result-badge " + (isUrgent ? "badge-urgent" : `badge-${sent.toLowerCase()}`);
            badge.textContent = isUrgent ? "URGENT (P1)" : sent.toUpperCase();
        }

        const polVal = item.sentiment?.polarity !== undefined ? item.sentiment.polarity : 0.0;
        const polStr = (polVal >= 0 ? "+" : "") + Number(polVal).toFixed(2);

        const polEl = document.getElementById("metricPolarity");
        if (polEl) polEl.textContent = polStr;

        const urgEl = document.getElementById("metricUrgency");
        if (urgEl) urgEl.textContent = isUrgent ? "Urgent (P1)" : "Standard (P2)";

        const themeEl = document.getElementById("metricTheme");
        if (themeEl) themeEl.textContent = (item.themes && item.themes.length) ? item.themes[0] : "General";

        const teamEl = document.getElementById("metricTeam");
        if (teamEl) teamEl.textContent = item.suggested_team || "Support";

        const expEl = document.getElementById("resultExplanation");
        if (expEl) expEl.textContent = item.triage_explanation || item.urgency?.explanation || "Analyzed successfully.";

        box.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
};

// update stat counters across top of dashboard
function updateSummaryCounters() {
    const total = allReviews.length;
    const pos = allReviews.filter(r => r.sentiment?.label === "Positive").length;
    const neg = allReviews.filter(r => r.sentiment?.label === "Negative").length;
    const neu = allReviews.filter(r => r.sentiment?.label === "Neutral").length;
    const urgent = allReviews.filter(r => r.urgency?.is_urgent).length;

    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl("countTotal", total);
    setEl("countPositive", pos);
    setEl("countNegative", neg);
    setEl("countNeutral", neu);
    setEl("countUrgent", urgent);
    setEl("feedCount", total);
}

// filter feed by category
window.setFilter = function(filter, el) {
    currentFilter = filter;
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    if (el) el.classList.add("active");
    renderFeed();
};

// render verified feed items into DOM
function renderFeed() {
    const list = document.getElementById("feedList");
    if (!list) return;

    let filtered = allReviews;
    if (currentFilter === "urgent") {
        filtered = allReviews.filter(r => r.urgency?.is_urgent);
    } else if (currentFilter !== "all") {
        filtered = allReviews.filter(r => r.sentiment?.label?.toLowerCase() === currentFilter);
    }

    if (!filtered.length) {
        list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text-muted);">No reviews match this filter.</div>';
        return;
    }

    list.innerHTML = filtered.map(r => {
        const isUrgent = r.urgency?.is_urgent;
        const sent = r.sentiment?.label || "Neutral";
        const badgeClass = isUrgent ? "badge-urgent" : `badge-${sent.toLowerCase()}`;
        const badgeText = isUrgent ? "URGENT (P1)" : sent;
        const polVal = r.sentiment?.polarity !== undefined ? r.sentiment.polarity : 0.0;
        const polStr = (polVal >= 0 ? "+" : "") + Number(polVal).toFixed(2);
        const themes = (r.themes || []).map(t => `<span class="theme-tag">${escapeHtml(t)}</span>`).join("");

        return `
            <div class="feed-item ${isUrgent ? 'urgent-item' : ''}">
                <div class="feed-item-top">
                    <span class="feed-item-product">${escapeHtml(r.product || 'Unknown')}</span>
                    <span class="result-badge ${badgeClass}">${badgeText}</span>
                </div>
                <div class="feed-item-date">${r.date || ''} • Polarity: ${polStr}</div>
                <div class="feed-item-text">${escapeHtml(r.text)}</div>
                <div class="feed-item-footer">
                    <div>${themes}</div>
                    <span>Route: <strong>${escapeHtml(r.suggested_team || 'Support')}</strong></span>
                </div>
            </div>`;
    }).join("");
}

function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
}

// initialize dashboard on page load
document.addEventListener("DOMContentLoaded", () => {
    updateSummaryCounters();
    renderFeed();

    const form = document.getElementById("analyseForm");
    if (form) {
        form.addEventListener("submit", window.handleAnalyse);
    }
});
