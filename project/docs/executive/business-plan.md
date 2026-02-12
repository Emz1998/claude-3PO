# Business Plan

**Company:** Avaris
**Product:** Avaris
**Author:** emhar / Founder
**Version:** v1.0
**Last Updated:** 2026-02-09

---

## Executive Summary

**What:** Avaris is an ML-powered website that delivers daily NBA game predictions as SEO-optimized blog posts with a live, public performance dashboard.

**For whom:** Casual and serious NBA sports bettors in the US who want transparent, data-driven picks they can verify.

**Problem:** Most NBA prediction services ("tout services") cherry-pick results, hide losing streaks, and provide no verifiable track record, leaving bettors paying for unaccountable advice.

**Solution:** Avaris uses an XGBoost model retrained nightly on NBA Stats API data to generate daily moneyline predictions published with full public transparency, including probability percentages and a verifiable win/loss dashboard.

**Market:** The US NBA betting market is valued at $10B (2024) growing to $17.45B by 2032 (7% CAGR), with 29M estimated NBA bettors in the US.

**Business model:** Ad-supported free tier with SEO-driven organic traffic (Phase 1), then premium subscriptions at $19.99-29.99/month plus sportsbook affiliate commissions (Phase 2+).

**Traction:** Pre-launch. MVP targeting Q1 2026 with automated daily prediction pipeline, performance dashboard, and ad monetization.

**Ask:** Bootstrapped, no raise planned. Building with minimal infrastructure costs (Vercel free tier, GitHub Actions, free NBA Stats API).

---

## Company Overview

**Mission**

Avaris exists to provide NBA bettors with transparent, ML-powered predictions backed by publicly verifiable performance data.

**Company Details**

- **Legal entity:** Not yet formed
- **Incorporated in:** TBD
- **Founded:** 2025
- **Headquarters:** Remote
- **Stage:** Pre-seed / Bootstrapped
- **Website:** Coming soon

**Founders and Key Team**

- **emhar** - Founder / Lead Engineer / ML Engineer - Solo developer with full-stack engineering and data science capabilities. Building the entire product: ML model, web application, and automated pipeline.

**Why this team?** emhar combines full-stack development, ML/data science, and sports domain knowledge to build the complete product without external dependencies. The solo founder model keeps burn rate near zero while validating the concept.

---

## Problem

**The Pain**

NBA bettors face a broken ecosystem of prediction services. Tout services charge $50-500+/month for picks with no verifiable track record. They cherry-pick winning streaks for marketing, hide losses, and provide no methodology transparency. The industry is unregulated with no oversight of performance claims. Meanwhile, bettors who do their own research spend hours per day analyzing stats, tracking line movements, and building spreadsheets, only to be influenced by emotional bias and cognitive shortcuts. To break even against the sportsbook vig, bettors need 52.4%+ accuracy, and most paid services cannot prove they clear this bar.

**Who Feels It Most?**

- **Casual NBA bettors** - Pain Level: H - Currently follow free picks from social media and sports sites - Picks are inconsistent, unverifiable, and often wrong
- **Serious NBA bettors** - Pain Level: H - Currently pay for tout services or build DIY spreadsheet models - Tout services lack accountability; DIY models require significant time and statistical expertise

**Market Validation**

- **Market research** - Source: Birches Health / Industry reports - Tout industry is "rife with individuals who outright lie about past successes"; consumer trust is the #1 barrier
- **Competitor traction** - Source: Action Network ($240M acquisition by Better Collective) - Massive exit validates demand for sports betting analytics and prediction content
- **Market size** - Source: Statista, Grand View Research - 29M estimated NBA bettors in US; basketball betting is the fastest-growing segment (7% CAGR)
- **Consumer sentiment** - Source: PlayToday, industry surveys - 45% of users willing to pay for exclusive sports insights; average annual spend per bettor is $3,284

---

## Solution

**Product Overview**

Avaris is a website that uses an XGBoost machine learning model to predict NBA game winners daily. The model retrains nightly on the latest NBA stats, generates predictions with probability percentages, and auto-publishes them as SEO-optimized blog posts. A public performance dashboard tracks every prediction so anyone can verify the model's actual track record, solving the transparency problem that plagues the tout industry.

**Key Features**

- **XGBoost prediction model (moneyline)** - Retrains nightly on latest NBA data and generates daily predictions with probability percentages - Solves: Lack of data-driven, consistent analysis
- **Auto-generated SEO blog posts** - Daily picks published as optimized content with team matchups, probabilities, and betting context - Solves: Bettors needing quick, accessible daily picks without hours of research
- **Public performance dashboard** - Live, verifiable win/loss record, ROI tracking, and historical results visible to everyone - Solves: Zero accountability and cherry-picked results from tout services
- **Automated prediction pipeline** - End-to-end automation from data ingestion to content publication with zero manual intervention - Solves: Scalability and consistency that manual analysis cannot match

**How It Works**

```
Step 1: XGBoost model retrains nightly on latest NBA data from stats.nba.com
    |
Step 2: Predictions generated for today's games with probability percentages
    |
Step 3: SEO-optimized blog post auto-generated and published to Avaris
    |
Step 4: User visits site to see daily picks and verify model performance on the public dashboard
```

**Why Now?**

- XGBoost and ML tooling have matured so a solo developer can build production-grade models
- NBA Stats API provides free programmatic access to rich game data
- US sports betting legalization has expanded to 38 states + DC, rapidly growing the addressable market
- AI/ML in sports betting is a $10.8B market growing at 21% CAGR, but no dominant consumer-facing NBA-specific ML service exists yet
- Consumer distrust of tout services has created a gap for a transparency-first product

---

## Market Analysis

**Market Size**

- **TAM (Total Addressable Market)** - $18.51B - US sports betting gross gaming revenue (2025), growing to $26.04B by 2030 at 7.07% CAGR
- **SAM (Serviceable Addressable Market)** - $10B - NBA betting market specifically (2024), growing to $17.45B by 2032 at 7% CAGR; basketball is the fastest-growing betting segment
- **SOM (Serviceable Obtainable Market)** - $1.5M-2.5M (est.) - Realistic Year 1-2 capture: 500-2,500 paid subscribers at $19.99-29.99/mo + ad/affiliate revenue from 50k-250k monthly visitors

**Target Market Segments**

- **Casual NBA bettors** - ~15M users (est.) - Willingness to pay: M - Accessibility: H - Priority: Primary
- **Serious NBA bettors** - ~3M users (est.) - Willingness to pay: H - Accessibility: M - Priority: Secondary
- **Sports content consumers** - ~10M+ users - Willingness to pay: L - Accessibility: H - Priority: Future (ad/affiliate monetization)

**Market Trends**

- **US legalization expansion** - 38 states + DC now legal, 20% of US adults placed a sports bet in 2025 (up from 12% in 2023), directly expanding Avaris's addressable audience
- **AI/ML adoption in betting** - $10.8B market growing to $60B by 2034 (21% CAGR); Action Network just launched AI Playbook assistant, validating consumer demand for AI-powered tools
- **Trust crisis in tout services** - Industry rife with scams and unverifiable claims; consumer skepticism creates an opening for a transparency-first product
- **Sports betting content growth** - SEO-optimized sports content sees 200% organic traffic increase in first year; sports has one of the lowest AI Overview shares (14.8%), protecting organic click-through rates

---

## Competitive Landscape

**Direct Competitors**

- **Action Network** - Sports betting media platform with expert picks, AI Playbook, live odds tracking - Strengths: $240M acquisition, 350M+ bets tracked, 10+ sportsbook partnerships - Weaknesses: Multi-sport generalist, premium pricing not transparent, affiliate bias concerns - Our advantage: NBA-specific ML focus, fully public performance dashboard, free tier with full transparency
- **BetQL** - Sports betting analytics with 5-star value ratings, simulates games 10,000 times - Strengths: Sophisticated simulation model, granular line movement tracking - Weaknesses: Expensive ($76.67/mo for 3-month plan), limited accuracy transparency, multi-sport dilutes NBA focus - Our advantage: Lower price point, public verifiable track record, NBA-only specialization
- **Dimers.com** - ML-powered prediction platform with Dimebot AI assistant and B2B white-label - Strengths: Transparent ML methodology, affordable pricing ($24.99/mo), B2B revenue - Weaknesses: Generic branding, limited brand awareness, multi-sport - Our advantage: NBA-specific depth, auto-generated SEO content creating organic traffic moat
- **OddsShark / Covers.com** - Free sports betting odds comparison and information aggregators - Strengths: Completely free, 18-30+ years of operation, strong SEO presence - Weaknesses: No proprietary ML models, affiliate bias, no advanced analytics - Our advantage: ML-powered predictions vs. opinion-based, verifiable accuracy metrics

**Indirect Competitors / Substitutes**

- **Traditional tout services ($50-500+/mo)** - Bettors pay handicappers for daily picks - They will switch because Avaris provides verifiable accuracy, transparent methodology, and a free tier that outperforms most paid touts
- **Manual research / spreadsheets** - Serious bettors spend hours analyzing stats and building models - They will switch because Avaris automates the analysis with a retrained ML model that removes emotional bias and saves hours daily
- **Free prediction sites (Pickswise, CBS Sports)** - Casual bettors use free expert picks with no ML sophistication - They will switch because Avaris offers ML-powered predictions with actual probability percentages and performance accountability

**Competitive Moat**

- **Transparency and trust** - Public performance dashboard with every prediction tracked creates trust that cannot be faked, directly addressing the #1 industry problem
- **SEO content compounding** - Daily auto-generated blog posts create an ever-growing library of indexed content, making organic traffic a compounding advantage over time
- **Continuously improving ML model** - Nightly retraining means the model improves as more data accumulates; competitors using static models or human analysis cannot match this feedback loop
- **NBA specialization** - Deep focus on one sport allows better feature engineering, model tuning, and domain expertise vs. generalist platforms spread across 10+ sports

---

## Business Model

**Revenue Streams**

- **Ad revenue (MVP)** - Model: Display ads (Google AdSense) + programmatic - Revenue: $2-5 RPM (est.) on sports content - Notes: Primary revenue from day one; scales with organic traffic
- **Sportsbook affiliate commissions (Phase 2)** - Model: CPA ($50-200/FTD) + RevShare (15-40% NGR) - Revenue: $5,000-50,000/mo at scale (est.) - Notes: Affiliate links in prediction posts; partner with 3-5 licensed sportsbooks
- **Premium subscriptions (Phase 3)** - Model: Monthly/annual subscription - Revenue: $19.99/mo or $149.99/yr - Notes: Advanced analytics, spread/totals predictions, real-time alerts, ad-free experience

**Pricing Strategy**

**Model:** Freemium (free tier + paid subscription)

- **Free** - $0 - Includes: Daily moneyline predictions, public performance dashboard, basic betting trends - Target: Casual bettors, SEO traffic, trust building
- **Pro** - $19.99/mo or $149.99/yr ($12.50/mo) - Includes: Advanced analytics, confidence scores, spread/totals, real-time alerts, email newsletter, ad-free - Target: Serious bettors who want deeper analysis
- **Annual Pro** - $149.99/yr (25% savings) - Includes: All Pro features + playoff predictions, futures analysis, priority support - Target: Committed bettors seeking long-term value

**Pricing rationale:** $19.99/mo undercuts BetQL ($76.67/mo) and competes with Dimers ($24.99/mo) and Rithmm ($29.99/mo). Free tier is essential to build trust (the core differentiator) and drive SEO traffic. Annual discount drives commitment and reduces churn. 45% of sports bettors are willing to pay for exclusive insights.

**Unit Economics**

- **Average Revenue Per User** - $1.50/mo (est.) - Blended across free (ad/affiliate) and paid users
- **Customer Acquisition Cost** - ~$0-5 (est.) - Organic SEO and social media; no paid acquisition initially
- **Lifetime Value** - $108 (est.) - Based on avg retention of 8 months at $13.50/mo blended ARPU for paid users (est.)
- **LTV:CAC Ratio** - 21:1+ (est.) - Extremely favorable due to organic acquisition; will normalize as paid channels are added
- **Gross Margin** - ~90% (est.) - Key costs: hosting (Vercel), NBA Stats API (free), compute for model training
- **Payback Period** - <1 month (est.) - Near-zero CAC means immediate payback; will increase with paid acquisition

_All estimates marked (est.). Revisit after launch with real data._

---

## Go-To-Market Strategy

**Launch Strategy**

**Phase 1: MVP Launch (Q1 2026)**

- **Target:** Casual NBA bettors searching for daily predictions via Google
- **Channel:** SEO-optimized daily blog posts targeting long-tail keywords (e.g., "Lakers vs Celtics prediction today", "NBA picks [date]")
- **Goal:** 5,000 monthly visitors, automated pipeline running daily, ad revenue generating, 55%+ win rate over 50+ predictions

**Phase 2: Growth (Q2-Q3 2026)**

- **Target:** Broader NBA bettor audience + email subscribers
- **Channel:** Social media (Twitter/X for real-time picks, Instagram Reels for win streaks), email newsletter, Reddit community engagement (r/sportsbook, r/NBA)
- **Goal:** 50,000 monthly visitors, 10,000 email subscribers, sportsbook affiliate partnerships established

**Acquisition Channels**

- **Organic SEO** - Daily auto-generated prediction posts targeting long-tail NBA keywords - Cost: Low (built into product) - Expected impact: Primary long-term traffic driver (200% growth Year 1)
- **Social media** - Twitter/X for real-time picks, Instagram Reels for performance highlights, Reddit for community engagement - Cost: Low (time only) - Expected impact: Medium-term brand building and referral traffic
- **Email newsletter** - Daily picks newsletter with 40.6% open rate benchmark (sports/recreation highest across industries) - Cost: Low ($0-50/mo for email service) - Expected impact: High retention and conversion channel
- **Sportsbook affiliates** - Affiliate partnerships with DraftKings, FanDuel, BetMGM for revenue share and co-marketing - Cost: Medium (integration work) - Expected impact: High revenue per conversion ($50-200 CPA per referred depositor)

**Retention Strategy**

- Daily fresh predictions create a habit loop, users return every morning to check picks for today's games
- The "aha moment" is seeing the public dashboard prove accuracy over 50+ predictions, converting skeptics into believers
- Transparent track record and email reminders prevent churn; users who verify accuracy become evangelists

---

## Financial Projections

_Conservative estimates. All assumptions clearly marked._

**Revenue Forecast**

- **Month 3** - Free users: 3,000 - Paid users: 0 - Conversion: 0% (pre-subscription) - MRR: $150 (est., ads only) - ARR: $1,800 (est.)
- **Month 6** - Free users: 10,000 - Paid users: 0 - Conversion: 0% (pre-subscription) - MRR: $800 (est., ads + early affiliate) - ARR: $9,600 (est.)
- **Month 12** - Free users: 50,000 - Paid users: 250 - Conversion: 0.5% - MRR: $8,500 (est., $5k subs + $2k affiliate + $1.5k ads) - ARR: $102,000 (est.)
- **Month 24** - Free users: 250,000 - Paid users: 2,500 - Conversion: 1% - MRR: $72,500 (est., $50k subs + $15k affiliate + $7.5k ads) - ARR: $870,000 (est.)

**Cost Structure**

- **Hosting / Infrastructure** - $0-50/mo - Vercel free tier, GitHub Actions
- **AI/ML compute** - $0-20/mo - XGBoost training on free-tier cloud or local machine
- **Domain / Services** - $20/mo - Domain, email service, analytics tools
- **Marketing** - $0/mo (Phase 1), $500-2,000/mo (Phase 2+) - Organic-first; paid channels added after PMF
- **Salaries / Contractors** - $0/mo - Solo founder, bootstrapped
- **Total Monthly Burn** - **$20-90/mo (Phase 1)**, **$540-2,090/mo (Phase 2+)**

**Key Assumptions**

1. **55%+ win rate achievable** - Sensitivity: If <52.4%, no credible value proposition; if 60%+, significantly accelerates growth
2. **0.5-1% free-to-paid conversion** - Sensitivity: If 0.25%: $51k ARR at Month 12. If 2%: $204k ARR at Month 12
3. **SEO drives 200% organic traffic growth Year 1** - Sensitivity: If 100%: Half the visitor/revenue projections. If 300%: 1.5x projections
4. **Average paid retention: 8 months** - Sensitivity: If 4 months: LTV drops to $80. If 12 months: LTV rises to $240

**Path to Profitability**

With near-zero burn rate ($20-90/mo), Avaris is effectively profitable from the first dollar of ad revenue. The real question is when revenue justifies full-time focus. At $8,500/mo MRR (Month 12 target), the product generates meaningful income. At $72,500/mo MRR (Month 24 target), it supports a small team and reinvestment. The bootstrapped model means no investor pressure to scale prematurely.

---

## Funding and Use of Funds

**Current Status**

- **Funding raised:** Self-funded ($0 external)
- **Current runway:** Indefinite (near-zero burn, bootstrapped)
- **Seeking:** Not raising. Bootstrapped model with organic growth.

_No external funding required for MVP or Phase 2. Revisit if scaling requires paid acquisition or team expansion._

---

## Risks and Mitigations

- **Model accuracy below 55%** - Category: Technical - Impact: H - Likelihood: M - Mitigation: Backtest on 2+ seasons, paper trade before launch, use time-series cross-validation, iterate on features
- **Low organic traffic / SEO competition** - Category: Market - Impact: M - Likelihood: M - Mitigation: Target long-tail keywords ("[Team] vs [Team] prediction [date]"), build email list, diversify to social channels
- **NBA Stats API rate limiting or deprecation** - Category: Technical - Impact: M - Likelihood: L - Mitigation: Cache data aggressively, build scraping fallback, explore alternative data providers
- **Competitor launches similar transparency product** - Category: Competitive - Impact: M - Likelihood: M - Mitigation: First-mover advantage on public dashboard, SEO content library creates compounding moat, NBA specialization
- **AI Overviews reduce click-through rates** - Category: Market - Impact: M - Likelihood: M - Mitigation: Sports content has lowest AI Overview share (14.8%); diversify traffic via email, social, and direct
- **AI API cost escalation (future premium features)** - Category: Financial - Impact: L - Likelihood: M - Mitigation: XGBoost runs locally (no API dependency for core model); token budgets for any future LLM features
- **Founder burnout (solo developer)** - Category: Team - Impact: H - Likelihood: M - Mitigation: Automate everything possible, scope discipline per constitution, sustainable pace, defer features aggressively

---

## Milestones and Timeline

- **Build (Month 1-3, Q1 2026)** - Key milestones: MVP complete, XGBoost model trained and backtested, automated pipeline running, performance dashboard live - Success metric: 55%+ win rate over 50+ backtested predictions, daily automation working
- **Launch (Month 3, end of Q1 2026)** - Key milestones: Public launch, first real predictions published, Google AdSense integrated - Success metric: Automated daily predictions live, ad revenue generating, no critical bugs
- **Validate (Month 4-6, Q2 2026)** - Key milestones: 50+ live predictions tracked, SEO traffic growing, email list building - Success metric: 55%+ live win rate, 10k+ monthly visitors, 500+ email subscribers
- **Grow (Month 7-12, Q3-Q4 2026)** - Key milestones: Affiliate partnerships, social media presence, subscription tier launched - Success metric: 50k monthly visitors, 250 paid subscribers, $8.5k MRR
- **Sustain (Month 13+, 2027)** - Key milestones: Scale acquisition, expand to spread/totals, prediction bot beta - Success metric: 250k monthly visitors, 2,500 paid subscribers, $72.5k MRR

---

## Appendix

**Glossary**

- **XGBoost** - Gradient boosting ML algorithm used for the prediction model
- **Moneyline** - A bet on which team will win the game outright
- **Spread** - A bet on the margin of victory
- **Totals (Over/Under)** - A bet on the combined score of both teams
- **Vig (Vigorish)** - The sportsbook's commission, requiring ~52.4% accuracy to break even
- **Tout service** - A paid sports prediction service, often with unverifiable track records
- **TAM/SAM/SOM** - Total Addressable Market / Serviceable Addressable Market / Serviceable Obtainable Market
- **MRR/ARR** - Monthly Recurring Revenue / Annual Recurring Revenue
- **CPA** - Cost Per Acquisition, a one-time payment per referred customer
- **RevShare** - Revenue share, an ongoing percentage of referred customer revenue
- **FTD** - First-Time Depositor, a new customer who deposits funds at a sportsbook
- **NGR** - Net Gaming Revenue, sportsbook revenue after paying out winnings

**References and Research**

- Statista - US Sports Betting Market Forecast (2025-2030)
- Grand View Research - US Sports Betting Market Report 2030
- Market Research Intellect - Basketball Betting Market 2033
- IMARC Group - US Sports Betting Market Report 2034
- TrafficGuard - US Sports Betting Market Trends 2026
- PlayToday - How Much Money Do Americans Bet on Sports
- Birches Health - Sports Betting Demographics and Touts Analysis
- Legal Sports Report - Sports Betting States Tracker
- VegasInsider - AI in Sports Betting 2026
- Intellias - AI in Sports Betting Market Analysis
- Action Network, BetQL, Dimers, OddsShark, Covers - Competitor pricing and features
- Fortis Media - SEO Tips for Sports Websites 2026
- MailerLite - Email Marketing Benchmarks 2025
- Olavivo - Top Sports Betting Affiliate Programs

**Supporting Documents**

- **Product Vision** - `project/docs/executive/product-vision.md` - Strategic direction and MVP scope
- **Product Brief** - `project/docs/product/product-brief.md` - Tactical build plan (to be completed)
- **Architecture** - `project/docs/architecture.md` - Technical architecture decisions

---

## Document History

- **v1.0** - 2026-02-09 - emhar - Initial draft based on market research
