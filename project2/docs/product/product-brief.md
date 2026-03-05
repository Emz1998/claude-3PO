# Product Brief

**Project:** Avaris
**Version:** v1.0
**Last Updated:** 2026-02-10
**Product Vision:** `project/docs/executive/product-vision.md`

---

## One-Liner

NEXLY is an ML-powered prediction website that delivers daily NBA picks with a public performance dashboard for sports bettors who want transparent, verifiable predictions.

---

## Problem

**What's Broken Today?**

NBA bettors pay $50-500+/month for tout services with no verifiable track records. These services cherry-pick wins, hide losses, and offer zero methodology transparency. Bettors who do their own research spend hours daily on manual analysis that still falls prey to emotional bias. To break even against the vig, 52.4%+ accuracy is needed, and most paid services can't prove they clear that bar.

**Evidence**

- **Industry research (Birches Health)** - Tout industry is "rife with individuals who outright lie about past successes"
- **Competitor validation** - Action Network acquired for $240M by Better Collective, validating demand for sports betting analytics
- **Market size (Statista, Grand View Research)** - 29M estimated NBA bettors in US; basketball betting growing at 7% CAGR
- **Consumer sentiment (PlayToday)** - 45% of users willing to pay for exclusive sports insights; average annual spend per bettor is $3,284

---

## User Personas

**Primary: The Casual Bettor**

- **Who** - Recreational NBA bettor, 25-45, bets weekly during NBA season
- **Context** - Checks predictions on phone/desktop before placing bets, usually mornings
- **Goal** - Quick, reliable daily picks without hours of research
- **Frustration** - Free picks from social media are inconsistent and unverifiable
- **Tech comfort** - Medium
- **Story role** - "casual bettor"

**Secondary: The Serious Bettor**

- **Who** - Analytics-savvy bettor, 25-55, bets daily with larger stakes
- **Context** - Reviews data and models before placing bets, values methodology
- **Goal** - Advanced analytics, probability data, and proven track record to inform bets
- **Frustration** - Tout services lack accountability; DIY models require significant time
- **Tech comfort** - High
- **Story role** - "serious bettor"

---

## Core User Journey

1. User searches Google for "NBA predictions today" or "[Team] vs [Team] prediction"
2. User lands on NEXLY blog post with today's picks, probability percentages, and matchup context
3. User views the performance dashboard to verify the model's historical accuracy
4. User bookmarks the site or subscribes to email for daily picks
5. User returns daily to check predictions before placing bets

**Journey Narrative** - A casual bettor googles NBA picks for tonight's games, finds a NEXLY blog post with ML-generated predictions and confidence percentages, checks the public dashboard showing 55%+ accuracy over 100+ predictions, and trusts the picks enough to return daily.

---

## MVP Scope

**Features In**

- **XGBoost prediction model (moneyline)** - Retrains nightly, generates daily predictions with probability percentages (EP-001)
- **Auto-generated SEO blog posts** - Daily picks published as optimized content with team matchups and probabilities (EP-002)
- **Public performance dashboard** - Live win/loss record, ROI tracking, historical results visible to everyone (EP-003)
- **Automated prediction pipeline** - End-to-end automation from data ingestion to content publication (EP-004)
- **Google AdSense integration** - Display ads for revenue from day one (EP-005)

**Features Out (Explicitly Deferred)**

- **Subscription tiers / Stripe** - Need proven track record (55%+ over 100+ picks) before charging
- **Spread and totals predictions** - Moneyline first; expand after proving core model
- **Prediction bot (desktop app)** - Premium product deferred until model is proven
- **API access** - Requires auth infrastructure; defer until paying users exist
- **Mobile apps** - Web-first; mobile deferred to future phase
- **Multi-sport expansion** - Validate NBA first before expanding

---

## Design Constraints

**Platform**

- **Target platform** - Web (desktop-optimized, responsive)
- **Min screen size** - 1024px wide (desktop-first, mobile-friendly)
- **Offline support** - No (content requires server-rendered pages)
- **Browser requirements** - Chrome, Firefox, Safari, Edge (latest 2 versions)

**Performance**

- **Page load time** - < 2 seconds (SSG pages served from CDN)
- **Dashboard load** - < 3 seconds (includes data fetch)
- **Largest Contentful Paint** - < 2.5 seconds
- **Bundle size** - < 200KB first load JS

**Data and Privacy**

- **Auth method** - None for MVP (all content is public/free)
- **Data storage** - Firebase Firestore (predictions, results, performance data)
- **Privacy requirements** - No user data collected in MVP beyond standard analytics

---

## Tech Stack

- **Frontend** - Next.js 15 (React 19) + TypeScript
- **Styling** - Tailwind CSS v4
- **Backend** - Firebase (Firestore for data storage)
- **ML** - Python + XGBoost (prediction model)
- **Data source** - NBA Stats API (stats.nba.com)
- **Hosting** - Vercel (free tier)
- **CI/CD** - GitHub Actions (daily pipeline automation)
- **Ads** - Google AdSense
- **Testing** - Vitest (web), pytest (Python pipeline)
- **Linting** - ESLint + Prettier

---

## Timeline and Sprint Mapping

- **Sprint 1 (Feb 17 - Mar 2)** - Foundation: project setup, Next.js scaffold, Firebase config, XGBoost model v1
- **Sprint 2 (Mar 3 - Mar 16)** - Core loop: prediction pipeline, auto-generated blog posts, basic SEO
- **Sprint 3 (Mar 17 - Mar 30)** - Dashboard: performance tracking, historical results, data visualization
- **Sprint 4 (Mar 31 - Apr 13)** - Polish: AdSense integration, SEO optimization, bug fixes, launch prep

**Total timeline:** 8 weeks
**Ship date:** 2026-04-13

_This is a plan, not a promise. Adjust at each sprint close based on actual velocity._

---

## Success Criteria

**MVP Launch (Go / No-Go)**

- 55%+ win rate over 50+ predictions (beats ~52.4% break-even)
- Automated daily prediction pipeline running without manual intervention
- Performance dashboard live and publicly accessible
- Ad revenue generating (any amount)
- No critical bugs in daily picks or dashboard

**Post-Launch Validation**

- **User activation** - 5,000+ monthly visitors within 3 months (measured via Google Analytics)
- **Retention** - 30%+ return visitors within 7 days (measured via Google Analytics)
- **Engagement** - Average session duration > 2 minutes on prediction pages
- **Revenue** - $150+/month ad revenue by month 3

---

## Assumptions and Open Questions

**Assumptions**

- 55%+ win rate is achievable with XGBoost on NBA Stats API data (risk: no credible value proposition if < 52.4%)
- SEO-optimized daily content will drive organic traffic (risk: need to diversify if SEO underperforms)
- NBA Stats API remains free and accessible (risk: need scraping fallback if rate-limited)
- Users will trust a public dashboard as proof of accuracy (risk: may need third-party verification)

**Open Questions**

- Which specific NBA stats features yield the best XGBoost accuracy? (blocks EP-001)
- What's the optimal blog post format for SEO in sports prediction content? (blocks EP-002)
- Should predictions be generated pre-market or post-line-release? (blocks EP-001)
- How to handle games that are postponed or cancelled in the performance dashboard? (blocks EP-003)

---

## Document History

- **v1.0** - 2026-02-10 - emhar - Initial draft from product-vision.md and business-plan.md
