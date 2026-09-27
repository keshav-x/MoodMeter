// Curated Initial Dataset
        const INITIAL_REVIEWS = [
            {
                product: "AudioMax 500",
                text: "The audio clarity and active noise cancellation are superb. Battery lasted through an entire 14-hour flight. Highly recommend!",
                sentiment: { label: "Positive", polarity: 0.65 },
                themes: ["Product Quality"],
                urgency: { is_urgent: false },
                suggested_team: "Customer Experience"
            },
            {
                product: "FitBand Pro",
                text: "The mobile app refuses to sync my step count and crashes every time I open Bluetooth settings. Very frustrating bug.",
                sentiment: { label: "Negative", polarity: -0.42 },
                themes: ["App & Software"],
                urgency: { is_urgent: false },
                suggested_team: "Mobile & Web Engineering"
            },
            {
                product: "SmartWatch X1",
                text: "Safety alert: the charging port got burning hot and emitted a burning smell while plugged into the wall adapter overnight!",
                sentiment: { label: "Negative", polarity: -0.38 },
                themes: ["Safety & Health"],
                urgency: { is_urgent: true, explanation: "Flagged: safety hazard detected (fire, burning hot)." },
                suggested_team: "Legal and Safety Compliance"
            },
            {
                product: "SmartWatch X1",
                text: "Been waiting 3 weeks for my delivery with zero tracking updates. Customer support has not replied to my emails.",
                sentiment: { label: "Negative", polarity: -0.15 },
                themes: ["Shipping & Delivery"],
                urgency: { is_urgent: false },
                suggested_team: "Shipping Operations"
            },
            {
                product: "AudioMax 500",
                text: "Can I connect these headphones to two devices simultaneously via multipoint bluetooth? Please clarify battery specs.",
                sentiment: { label: "Neutral", polarity: 0.00 },
                themes: ["General Feedback"],
                urgency: { is_urgent: false },
                suggested_team: "General Support"
            }
        ];

        // Standalone Serverless Embedded NLP Lexicon & Triage Engine
        // Enables 100% full functionality on Vercel with ZERO server needed
        const LEXICON = {
            "love": 0.8, "superb": 0.9, "excellent": 0.9, "great": 0.7, "good": 0.5, "awesome": 0.8, "perfect": 0.9,
            "best": 0.8, "fantastic": 0.8, "happy": 0.6, "recommend": 0.6, "clarity": 0.4, "clean": 0.4,
            "terrible": -0.8, "worst": -0.9, "bad": -0.5, "poor": -0.6, "horrible": -0.9, "crash": -0.7,
            "crashes": -0.7, "frustrating": -0.6, "bug": -0.5, "broken": -0.7, "fails": -0.6, "refuses": -0.4,
            "hate": -0.8, "disappointed": -0.6, "burning": -0.4, "hot": -0.2, "smell": -0.2, "defect": -0.6,
            "delayed": -0.4, "waiting": -0.2, "slow": -0.3, "expensive": -0.3, "waste": -0.7, "refund": -0.5
        };

        const SAFETY_TRIGGERS = [
            "safety", "hazard", "injury", "hurt", "allergic", "health", "dangerous", "toxic",
            "fire", "smoke", "burn", "burning", "overheat", "overheating", "exploded", "explosion", "spark", "shock"
        ];

        const THEME_DICTIONARY = {
            "Safety & Health": ["fire", "smoke", "burn", "burning", "hot", "overheat", "spark", "shock", "hazard", "allergic", "injury"],
            "App & Software": ["app", "software", "bluetooth", "sync", "syncing", "crash", "crashes", "update", "bug", "connect"],
            "Product Quality": ["battery", "audio", "clarity", "sound", "hardware", "material", "durability", "casing", "screen"],
            "Shipping & Delivery": ["shipping", "delivery", "delivered", "package", "tracking", "order", "waiting", "weeks"],
            "Pricing & Billing": ["price", "pricing", "charge", "refund", "billing", "cost", "subscription", "expensive"]
        };

        function evaluateClientSideNLP(text, product) {
            const lower = text.toLowerCase();
            const words = lower.replace(/[^a-z0-9\s]/g, " ").split(/\s+/);

            // 1. Polarity calculation
            let totalScore = 0;
            let count = 0;
            for (let i = 0; i < words.length; i++) {
                const w = words[i];
                if (LEXICON[w] !== undefined) {
                    let score = LEXICON[w];
                    // Check negation
                    if (i > 0 && ["not", "no", "never", "hardly", "without"].includes(words[i - 1])) {
                        score = -score * 0.8;
                    }
                    // Check intensifier
                    if (i > 0 && ["very", "extremely", "really", "so"].includes(words[i - 1])) {
                        score = score * 1.3;
                    }
                    totalScore += score;
                    count++;
                }
            }

            let polarity = count > 0 ? (totalScore / count) : 0.0;
            polarity = Math.max(-1.0, Math.min(1.0, polarity));

            let label = "Neutral";
            if (polarity > 0.1) label = "Positive";
            else if (polarity < -0.1) label = "Negative";

            // 2. Theme detection
            const matchedThemes = [];
            for (const [theme, kwList] of Object.entries(THEME_DICTIONARY)) {
                if (kwList.some(k => lower.includes(k))) {
                    matchedThemes.push(theme);
                }
            }
            if (matchedThemes.length === 0) matchedThemes.push("General Feedback");

            // 3. Safety Hazard check
            const matchedSafety = SAFETY_TRIGGERS.filter(k => lower.includes(k));
            const isUrgent = matchedSafety.length > 0;

            // 4. Department routing
            let team = "General Support";
            if (isUrgent || matchedThemes.includes("Safety & Health")) team = "Legal and Safety Compliance";
            else if (matchedThemes.includes("App & Software")) team = "Mobile & Web Engineering";
            else if (matchedThemes.includes("Product Quality")) team = "Hardware Engineering";
            else if (matchedThemes.includes("Shipping & Delivery")) team = "Shipping Operations";
            else if (matchedThemes.includes("Pricing & Billing")) team = "Finance Operations";
            else if (label === "Positive") team = "Customer Experience";

            const explanation = isUrgent
                ? `Flagged: safety hazard detected (${matchedSafety.slice(0, 2).join(', ')}). Immediate routing to ${team}.`
                : `Polarity score: ${polarity.toFixed(2)}. Themes: ${matchedThemes.join(', ')}. Routing: ${team}.`;

            return {
                product: product || "General Feedback",
                text: text,
                sentiment: { label: label, polarity: polarity },
                themes: matchedThemes,
                urgency: { is_urgent: isUrgent, explanation: explanation },
                suggested_team: team,
                triage_explanation: explanation
            };
        }

        const EXAMPLES = {
            positive: {
                product: "AudioMax 500",
                text: "The audio clarity and active noise cancellation are superb. Battery lasted through an entire 14-hour flight. Highly recommend!"
            },
            negative: {
                product: "FitBand Pro",
                text: "The mobile app refuses to sync my step count and crashes every time I open Bluetooth settings. Very frustrating bug."
            },
            safety: {
                product: "SmartWatch X1",
                text: "Safety alert: the charging port got burning hot and emitted a burning smell while plugged into the wall adapter overnight!"
            }
        };

        function fillExample(type) {
            const ex = EXAMPLES[type];
            if (!ex) return;
            document.getElementById('productName').value = ex.product;
            document.getElementById('reviewText').value = ex.text;
            handleAnalyse(new Event('submit'));
        }

        let allReviews = INITIAL_REVIEWS.slice();
        let currentFilter = 'all';

        function updateSummaryCounters() {
            const total = allReviews.length;
            const pos = allReviews.filter(r => r.sentiment?.label === "Positive").length;
            const neg = allReviews.filter(r => r.sentiment?.label === "Negative").length;
            const neu = allReviews.filter(r => r.sentiment?.label === "Neutral").length;
            const urgent = allReviews.filter(r => r.urgency?.is_urgent).length;

            document.getElementById('statTotal').textContent = total;
            document.getElementById('statPositive').textContent = pos;
            document.getElementById('statNeutral').textContent = neu;
            document.getElementById('statNegative').textContent = neg;
            document.getElementById('statUrgent').textContent = urgent;
        }

        async function loadSummary() {
            try {
                const res = await fetch('/api/summary');
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('statTotal').textContent = data.total_reviews || 0;
                    document.getElementById('statPositive').textContent = data.sentiment_distribution?.positive || 0;
                    document.getElementById('statNeutral').textContent = data.sentiment_distribution?.neutral || 0;
                    document.getElementById('statNegative').textContent = data.sentiment_distribution?.negative || 0;
                    document.getElementById('statUrgent').textContent = data.urgent_count || 0;
                    return;
                }
            } catch (err) {}
            updateSummaryCounters();
        }

        async function loadReviews() {
            try {
                const res = await fetch('/api/reviews');
                if (res.ok) {
                    const data = await res.json();
                    if (data.reviews && data.reviews.length > 0) {
                        allReviews = data.reviews;
                    }
                }
            } catch (err) {}
            renderFeed();
        }

        function setFilter(filter, el) {
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            el.classList.add('active');
            renderFeed();
        }

        function renderFeed() {
            const list = document.getElementById('feedList');
            let filtered = allReviews;

            if (currentFilter === 'positive') {
                filtered = allReviews.filter(r => (r.sentiment?.label || '').toLowerCase() === 'positive');
            } else if (currentFilter === 'negative') {
                filtered = allReviews.filter(r => (r.sentiment?.label || '').toLowerCase() === 'negative');
            } else if (currentFilter === 'urgent') {
                filtered = allReviews.filter(r => r.urgency?.is_urgent === true);
            }

            document.getElementById('feedCount').textContent = filtered.length;

            if (filtered.length === 0) {
                list.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 32px 0;">No reviews match this filter.</div>';
                return;
            }

            list.innerHTML = filtered.map(r => {
                const isUrgent = r.urgency?.is_urgent;
                const sentimentLabel = r.sentiment?.label || 'Neutral';
                const badgeClass = isUrgent ? 'badge-urgent' : `badge-${sentimentLabel.toLowerCase()}`;
                const badgeText = isUrgent ? 'Urgent Alert' : sentimentLabel;
                const polarityVal = r.sentiment?.polarity !== undefined ? (r.sentiment.polarity >= 0 ? '+' : '') + r.sentiment.polarity.toFixed(2) : '0.00';
                const themes = (r.themes || []).map(t => `<span class="theme-tag">${escapeHtml(t)}</span>`).join('');

                return `
                    <div class="feed-item">
                        <div class="feed-item-top">
                            <span class="feed-item-product">${escapeHtml(r.product || 'General Feedback')}</span>
                            <span class="result-badge ${badgeClass}">${badgeText}</span>
                        </div>
                        <div class="feed-item-text">${escapeHtml(r.text)}</div>
                        <div class="feed-item-footer">
                            <div>${themes || '<span class="theme-tag">General</span>'}</div>
                            <div>Polarity: <strong>${polarityVal}</strong> &bull; Routing: <strong>${escapeHtml(r.suggested_team || 'Support')}</strong></div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async function handleAnalyse(e) {
            if (e && e.preventDefault) e.preventDefault();
            const text = document.getElementById('reviewText').value.trim();
            const product = document.getElementById('productName').value.trim();
            if (!text) return;

            const btn = document.getElementById('btnSubmit');
            btn.disabled = true;
            btn.textContent = 'Analysing...';

            let item = null;

            // Try backend API first (when running Flask locally)
            try {
                const res = await fetch('/api/analyse', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ review: { text: text, product: product || 'General Feedback' } })
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.results && data.results[0]) {
                        item = data.results[0];
                    }
                }
            } catch (err) {
                // Backend server not available (e.g. static Vercel deployment)
            }

            // Seamless Serverless Fallback
            if (!item) {
                item = evaluateClientSideNLP(text, product);
            }

            // Update output display
            const box = document.getElementById('resultBox');
            const badge = document.getElementById('resultBadge');
            const isUrgent = item.urgency?.is_urgent;
            const sentimentLabel = item.sentiment?.label || 'Neutral';

            badge.className = 'result-badge ' + (isUrgent ? 'badge-urgent' : `badge-${sentimentLabel.toLowerCase()}`);
            badge.textContent = isUrgent ? 'Urgent Safety Flag' : sentimentLabel;

            const pol = item.sentiment?.polarity !== undefined ? item.sentiment.polarity : 0;
            document.getElementById('metricPolarity').textContent = (pol >= 0 ? '+' : '') + pol.toFixed(2);
            document.getElementById('metricUrgency').textContent = isUrgent ? 'Escalate Immediately' : 'Standard Priority';
            document.getElementById('metricTheme').textContent = (item.themes && item.themes.length > 0) ? item.themes[0] : 'General';
            document.getElementById('metricTeam').textContent = item.suggested_team || 'Customer Support';
            document.getElementById('resultExplanation').textContent = item.triage_explanation || 'Evaluation completed.';

            box.style.display = 'block';

            // Add to active feed and refresh counts
            allReviews.unshift(item);
            renderFeed();
            updateSummaryCounters();

            btn.disabled = false;
            btn.textContent = 'Run Analysis';
        }

        function escapeHtml(s) {
            if (!s) return '';
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }

        window.addEventListener('DOMContentLoaded', () => {
            loadReviews();
            loadSummary();
        });
