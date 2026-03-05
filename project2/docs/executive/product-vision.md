# Product Vision

**Project:** `Avaris`  
**Version:** `v0.1.0`  
**Author:** `emhar`  
**Last Updated:** `2025-12-13`

---

## Vision Statement

> **For** `casual and serious NBA bettors` **who** `lack access to transparent, data-driven game predictions`, **the** `Avaris` **is a** `ML-powered prediction service` **that** `delivers daily NBA picks with verifiable performance tracking`. **Unlike** `traditional tout services with questionable track records`, **our product** `provides full public transparency and accountability on every prediction`.

---

## The Problem

### Who Has This Problem?

| Segment             | Description                                                     | Size                          |
| ------------------- | --------------------------------------------------------------- | ----------------------------- |
| Casual NBA bettors  | Recreational bettors looking for quick, reliable daily picks    | ~15M US sports bettors (est.) |
| Serious NBA bettors | Analytics-savvy bettors wanting advanced data and premium tools | ~3M US (est.)                 |

### What's Broken Today?

Most NBA prediction services ("tout services") cherry-pick results, hide losing streaks, and provide no verifiable track record. Bettors either pay for unaccountable advice or spend hours doing manual research that still underperforms the vig.

### Why Now?

XGBoost and ML tooling have matured to the point where a solo developer can build production-grade models. The NBA Stats API provides free programmatic access to rich game data. US sports betting legalization continues expanding the addressable market rapidly.

---

## The Solution

Avaris is a website that uses machine learning to predict NBA game winners every day. It publishes picks as SEO-optimized blog posts with probability percentages, and shows a live performance dashboard so anyone can verify the model's track record. Free users get daily moneyline picks; premium users get spreads, totals, early access, and a downloadable prediction bot.

### Core Value Propositions

| #   | Value Proposition                    | User Benefit                                                                  |
| --- | ------------------------------------ | ----------------------------------------------------------------------------- |
| 1   | ML-powered daily predictions         | Data-driven picks that aim to beat the ~52.4% break-even rate                 |
| 2   | Full public performance transparency | Verifiable win rate, ROI, and recent results with no cherry-picking           |
| 3   | Tiered service (free + premium)      | Casual users get free picks; serious bettors get advanced analytics and tools |

### How It Works (High Level)

```
Step 1: XGBoost model retrains nightly on latest NBA data
    ↓
Step 2: Predictions generated for today's games with probability percentages
    ↓
Step 3: SEO-optimized blog post auto-generated and published
    ↓
Step 4: User visits site to see daily picks and performance dashboard
```

---

## Market Landscape

### Competitive Positioning

| Competitor / Alternative | What They Do                     | Their Weakness                                    | Our Advantage                                                  |
| ------------------------ | -------------------------------- | ------------------------------------------------- | -------------------------------------------------------------- |
| Tout services            | Sell picks via subscriptions     | Unverifiable track records, cherry-picked results | Full public transparency and accountability                    |
| Manual research          | Bettors analyze stats themselves | Time-consuming, inconsistent, emotional bias      | Automated ML model removes bias and saves time                 |
| Free prediction sites    | Generic picks with basic stats   | Low accuracy, no ML, no accountability            | XGBoost model with daily retraining and verifiable performance |

### Defensibility

Continuously retrained ML model that improves over time, accumulated public performance track record that builds trust, SEO-driven organic traffic moat from daily content, and the "prediction bot" desktop product creates switching costs and perceived exclusivity.

---

## Strategy

### MVP Scope

> Ad-supported blog with daily ML-powered NBA picks and a public performance dashboard.

**Target milestone:** `Q1 2026`
**Target user:** `Casual NBA bettors`

| Feature                       | Why It's in MVP                                                  |
| ----------------------------- | ---------------------------------------------------------------- |
| XGBoost model (moneyline)     | Core product — predictions are the value                         |
| Next.js blog with daily picks | SEO-optimized content drives organic traffic and builds audience |
| Performance dashboard         | Transparency is the key differentiator from competitors          |
| Automated prediction pipeline | Daily content requires zero manual intervention to scale         |
| Google AdSense                | Revenue from day one without requiring user commitment           |

### What's Explicitly NOT in MVP

| Excluded Feature             | Why Not Yet                                                                 |
| ---------------------------- | --------------------------------------------------------------------------- |
| Subscription tiers / Stripe  | Need proven track record (55%+ win rate over 100+ picks) before charging    |
| Spread & totals predictions  | Moneyline is simpler to validate; expand bet types after proving core model |
| Prediction bot (desktop app) | Premium product that only has value once the model is proven                |
| API access                   | Requires infrastructure and auth; defer until paying users exist            |
| Mobile apps                  | Desktop-first per project constitution; mobile deferred to future phase     |
| Multi-sport expansion        | Focus on NBA first; validate before expanding to NFL, MLB, NHL              |

### Product Roadmap (High Level)

| Phase       | Timeframe  | Theme                | Key Outcomes                                                                |
| ----------- | ---------- | -------------------- | --------------------------------------------------------------------------- |
| **MVP**     | Q1 2026    | Core prediction loop | Daily ML picks live, performance dashboard tracking, ad revenue generating  |
| **Phase 2** | Q2 2026    | Growth & prove       | SEO traffic at 10k+/month, email newsletter, social presence, model at 55%+ |
| **Phase 3** | Q3-Q4 2026 | Monetization         | Subscription tiers live, spread/totals predictions, prediction bot launched |

> This roadmap is directional, not a commitment. Priorities will shift based on user feedback and market signals.

---

## Business Model

### Revenue Model

| Model                   | Description                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------ |
| Ad-supported (MVP)      | Google AdSense initially, then affiliate links, then programmatic ad networks at 10k+ monthly visitors |
| Subscriptions (Phase 3) | Monthly subscription for premium features: spreads, totals, early access, API, prediction bot          |

### Key Metrics

| Metric            | Definition                             | MVP Target |
| ----------------- | -------------------------------------- | ---------- |
| Win rate          | % of moneyline predictions correct     | 55%+       |
| Monthly visitors  | Unique visitors per month              | 5k+        |
| MRR               | Monthly recurring revenue (ads + subs) | $1k-5k     |
| Email subscribers | Newsletter signups                     | 500+       |

### Unit Economics (If Known)

| Metric       | Value / Estimate | Notes                                                        |
| ------------ | ---------------- | ------------------------------------------------------------ |
| CAC          | ~$0 (est.)       | Organic SEO and social media — no paid acquisition initially |
| LTV          | TBD              | Depends on subscription conversion rate post-MVP             |
| LTV:CAC      | TBD              | Will calculate once subscription data available              |
| Gross Margin | ~90% (est.)      | Primary costs: hosting, API rate limits, model compute       |

> Pre-revenue. All estimates based on comparable sports prediction sites. Assumptions will be validated during MVP phase.

---

## Risks & Mitigations

| Risk                                      | Impact | Likelihood | Mitigation                                                                         |
| ----------------------------------------- | ------ | ---------- | ---------------------------------------------------------------------------------- |
| Model accuracy below 55%                  | H      | M          | Backtest on 2+ seasons, paper trade before launch, use time-series CV              |
| Low organic traffic / SEO competition     | M      | M          | Target long-tail keywords ("[Team] vs [Team] prediction [date]"), build email list |
| NBA Stats API rate limiting or changes    | M      | L          | Cache data aggressively, build scraping fallback for supplementary data            |
| Competitive response from funded startups | L      | M          | Transparency moat is hard to replicate; focus on trust and track record            |

---

## Team & Resources

| Role              | Who   | Status  |
| ----------------- | ----- | ------- |
| Founder / Lead    | emhar | Active  |
| Engineering       | emhar | Active  |
| ML / Data Science | emhar | Active  |
| Design            | TBD   | Planned |

### Current Runway / Budget

Bootstrapped. No external funding. Infrastructure costs minimal (Vercel free tier, GitHub Actions, free NBA Stats API).

---

## Success Criteria

### MVP Launch (Go / No-Go)

> What must be true to consider the MVP a success worth continuing?

- [ ] 55%+ win rate over 50+ predictions (beats ~52.4% break-even)
- [ ] Automated daily prediction pipeline running without manual intervention
- [ ] Performance dashboard live and publicly accessible
- [ ] Ad revenue generating (any amount)
- [ ] No critical bugs in daily picks or dashboard

### 6-Month Vision

Avaris has a publicly proven track record over 500+ predictions with a consistent 55%+ win rate. The site attracts 5k+ monthly visitors through SEO, has an active email newsletter, and generates meaningful ad revenue. The model's credibility is established and subscription launch is imminent.

### 12-Month Vision

Profitable NBA picks service with proven model (55%+ win rate), 10k+ monthly visitors, $1k-5k MRR from ads and early subscribers. Premium subscription tiers live with spread/totals predictions and early access features. The prediction bot desktop app is in beta, creating a unique product positioning in the market.

---

## Appendix

### Glossary

| Term                | Definition                                                           |
| ------------------- | -------------------------------------------------------------------- |
| XGBoost             | Gradient boosting ML algorithm used for the prediction model         |
| Moneyline           | A bet on which team will win the game outright                       |
| Spread              | A bet on the margin of victory                                       |
| Totals (Over/Under) | A bet on the combined score of both teams                            |
| Vig (Vigorish)      | The sportsbook's commission, requiring ~52.4% accuracy to break even |
| Tout service        | A paid sports prediction service                                     |
| Paper trading       | Running predictions without real stakes to validate accuracy         |

### References

- NBA Stats API (stats.nba.com) — primary data source
- Brainstorming session notes (2025-12-13)

---

## Document History

| Version | Date       | Author | Changes                                              |
| ------- | ---------- | ------ | ---------------------------------------------------- |
| 1.0     | 2025-12-13 | emhar  | Initial draft — converted from brainstorming session |
