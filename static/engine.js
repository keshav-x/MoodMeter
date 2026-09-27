// client-side sentiment analysis and triage engine for Vercel
const EXAMPLES = {
    praise: { text: "Outstanding build quality and crystal clear sound. Absolutely love it!", product: "AudioMax Pro" },
    bug: { text: "App keeps crashing on startup and Bluetooth disconnects constantly.", product: "FitBand Plus" },
    hazard: { text: "The charger got burning hot and emitted smoke overnight.", product: "SmartWatch X1" }
};

const INITIAL_REVIEWS = [
    { id: "MM-0001", text: "Outstanding build quality and crystal clear sound. Battery life lasts 2 days.", product: "AudioMax Pro", date: "2026-06-15", sentiment: { label: "Positive", polarity: 0.65 }, themes: ["Product Quality"], urgency: { is_urgent: false }, suggested_team: "Product Management", triage_explanation: "Routed to Product Management as positive customer feedback." },
    { id: "MM-0002", text: "App keeps crashing on startup after the latest update. Bluetooth disconnects.", product: "FitBand Plus", date: "2026-06-22", sentiment: { label: "Negative", polarity: -0.55 }, themes: ["App & Software"], urgency: { is_urgent: true }, suggested_team: "Mobile & QA Engineering", triage_explanation: "Urgent bug report: customer reports crash/severe malfunction." },
    { id: "MM-0003", text: "The charging port got burning hot and emitted smoke. Potential fire hazard.", product: "SmartWatch X1", date: "2026-07-01", sentiment: { label: "Negative", polarity: -0.38 }, themes: ["Safety & Health"], urgency: { is_urgent: true }, suggested_team: "Legal and Safety Compliance", triage_explanation: "Flagged: safety hazard detected. Immediate routing to Legal and Safety Compliance." },
    { id: "MM-0004", text: "Package arrived 6 days late and the outer box was severely crushed.", product: "AudioMax Pro", date: "2026-07-10", sentiment: { label: "Negative", polarity: -0.42 }, themes: ["Shipping & Delivery"], urgency: { is_urgent: false }, suggested_team: "Logistics & Fulfillment", triage_explanation: "Assigned to Logistics & Fulfillment for review and follow-up." },
    { id: "MM-0005", text: "Does this model support multipoint Bluetooth pairing with two laptops?", product: "AudioMax Pro", date: "2026-07-18", sentiment: { label: "Neutral", polarity: 0.05 }, themes: ["General Feedback"], urgency: { is_urgent: false }, suggested_team: "Customer Support", triage_explanation: "Logged for Customer Support monitoring." }
];

const LEXICON = {
    great: 0.8, good: 0.6, excellent: 0.9, love: 0.8, outstanding: 0.9, clear: 0.5,
    bad: -0.6, terrible: -0.9, worst: -0.9, poor: -0.7, broken: -0.8, defect: -0.8,
    crash: -0.8, smoke: -0.7, burning: -0.7, fire: -0.8, late: -0.5, crushed: -0.7
};

const HAZARDS = ["fire", "smoke", "spark", "burn", "shock", "exploded", "melted", "overheat"];
const THEMES = {
    "Safety & Health": ["fire", "smoke", "spark", "burn", "shock", "hazard", "overheat", "exploded"],
    "Product Quality": ["quality", "sound", "battery", "build", "broken", "durability", "hardware"],
    "App & Software": ["app", "software", "crash", "bug", "bluetooth", "sync", "freeze"],
    "Shipping & Delivery": ["shipping", "delivery", "late", "package", "box", "damaged"],
    "Customer Service": ["support", "service", "agent", "rep", "ticket", "refund"]
};

function fillExample(type) {
    const ex = EXAMPLES[type];
    if (!ex) return;
    document.getElementById("reviewText").value = ex.text;
    document.getElementById("productName").value = ex.product;
}

let allReviews = [...INITIAL_REVIEWS];
let currentFilter = "all";

function evaluateClientSideNLP(text, product) {
    const lower = text.toLowerCase();
    const words = lower.replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter(Boolean);
    let total = 0, count = 0;
    words.forEach(w => { if (LEXICON[w] !== undefined) { total += LEXICON[w]; count++; } });
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
    let explanation = "Logged for review.";
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
        text, product: product || "Unknown",
        date: new Date().toISOString().slice(0, 10),
        sentiment: { label, polarity },
        themes: matchedThemes,
        urgency: { is_urgent: isUrgent, explanation: isUrgent ? "Flagged as urgent priority." : "Standard priority." },
        suggested_team: team,
        triage_explanation: explanation
    };
}

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

function setFilter(filter, el) {
    currentFilter = filter;
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    if (el) el.classList.add("active");
    renderFeed();
}

function renderFeed() {
    const list = document.getElementById("feedList");
    if (!list) return;
    let filtered = allReviews;
    if (currentFilter === "urgent") filtered = allReviews.filter(r => r.urgency?.is_urgent);
    else if (currentFilter !== "all") filtered = allReviews.filter(r => r.sentiment?.label?.toLowerCase() === currentFilter);

    if (!filtered.length) {
        list.innerHTML = '<div style="padding:24px;text-align:center;color:#78716C;">No reviews match this filter.</div>';
        return;
    }

    list.innerHTML = filtered.map(r => {
        const isUrgent = r.urgency?.is_urgent;
        const sent = r.sentiment?.label || "Neutral";
        const badgeClass = isUrgent ? "badge-urgent" : `badge-${sent.toLowerCase()}`;
        const badgeText = isUrgent ? "Urgent Alert" : sent;
        const pol = r.sentiment?.polarity !== undefined ? (r.sentiment.polarity >= 0 ? "+" : "") + Number(r.sentiment.polarity).toFixed(2) : "0.00";
        const themes = (r.themes || []).map(t => `<span class="theme-tag">${escapeHtml(t)}</span>`).join("");
        return `
            <div class="feed-item ${isUrgent ? 'urgent-item' : ''}">
                <div class="feed-item-header">
                    <div class="feed-meta">
                        <span class="badge ${badgeClass}">${badgeText}</span>
                        <span class="feed-product">${escapeHtml(r.product || 'Unknown')}</span>
                        <span class="feed-date">${r.date || ''}</span>
                    </div>
                    <span class="polarity-pill">Polarity: ${pol}</span>
                </div>
                <div class="feed-text">${escapeHtml(r.text)}</div>
                <div class="feed-footer">
                    <div class="themes-list">${themes}</div>
                    <span class="feed-team">-> ${escapeHtml(r.suggested_team || 'Support')}</span>
                </div>
            </div>`;
    }).join("");
}

function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
    updateSummaryCounters();
    renderFeed();

    const form = document.getElementById("singleReviewForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = document.getElementById("reviewText").value.trim();
        const product = document.getElementById("productName").value.trim() || "General Product";
        if (!text) return;

        let item = null;
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

        if (!item) item = evaluateClientSideNLP(text, product);

        allReviews.unshift(item);
        updateSummaryCounters();
        renderFeed();

        const box = document.getElementById("resultBox");
        if (box) {
            box.style.display = "block";
            const isUrgent = item.urgency?.is_urgent;
            const sent = item.sentiment?.label || "Neutral";
            const badge = document.getElementById("resultBadge");
            if (badge) {
                badge.className = "badge " + (isUrgent ? "badge-urgent" : `badge-${sent.toLowerCase()}`);
                badge.textContent = isUrgent ? "Urgent Alert" : sent;
            }
            document.getElementById("resultTeam").textContent = item.suggested_team || "Support";
            document.getElementById("resultTriage").textContent = item.triage_explanation || "";
            const pol = item.sentiment?.polarity !== undefined ? (item.sentiment.polarity >= 0 ? "+" : "") + Number(item.sentiment.polarity).toFixed(2) : "0.00";
            document.getElementById("resultPolarity").textContent = pol;
            document.getElementById("resultThemes").textContent = (item.themes || []).join(", ");
            box.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    });
});
