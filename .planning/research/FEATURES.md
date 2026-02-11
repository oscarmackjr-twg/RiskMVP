# Feature Landscape

**Domain:** Institutional Portfolio Analytics Platform (Loan-Heavy Fixed Income)
**Researched:** 2026-02-11
**User Context:** Internal risk team at investment firm (not bank, lighter regulatory burden)
**Portfolio Mix:** 70%+ loans, plus bonds, ABS/MBS, derivatives hedges; thousands of positions

## Table Stakes

Features users expect. Missing any = platform feels incomplete or unusable.

| Feature | Why Expected | Complexity | Status in MVP | Notes |
|---------|--------------|------------|---------------|-------|
| **Portfolio upload & management** | Users need way to get positions in; essential for any analytics platform | High | Partial (JSON upload, basic portfolio node tracking) | Needs: portfolio hierarchy CRUD, holdings import from custodian feeds, historical snapshots for time-series |
| **Instrument master (loans, bonds, ABS/MBS)** | Can't price what you don't know; need standardized instrument definitions | High | Missing (demo only) | Must support: loan terms (amort sched, coupon), bond specs (maturity, callable), ABS/MBS (WAM, WAL, pool factors) |
| **Pricing for all asset types** | Core competency; team can't run portfolio analytics without instrument valuation | High | Partial (loan, fixed bond, FX; missing: floating, callable/putable, ABS/MBS, derivatives) | Needs: floating-rate pricers, callable/putable bond OAS models, ABS/MBS prepayment models, swap/swaption pricers |
| **Market data management** | Pricers need inputs; rates curves, spreads, FX must be versioned and available | High | Partial (snapshot ingestion; limited scenarios) | Needs: multi-curve setup (OIS, Libor, prime), credit spreads per rating/sector, historical data, data validation |
| **Risk measures (DV01, spread duration, OAS)** | Every risk team starts with "what if rates move?"; missing = can't do risk work | High | Partial (PV, DV01, FX_DELTA, ACCRUED_INTEREST only) | Needs: spread duration, key-rate duration, convexity, YTM, par spread, Z-spread, OAS |
| **Scenario & sensitivity analysis** | "Show me P&L under parallel rate shock + credit spread widening" is day-one workflow | High | Partial (BASE, RATES_PARALLEL_1BP, SPREAD_25BP, FX_SPOT_1PCT only) | Needs: user-defined scenarios, shock combinations, Monte Carlo paths, historical stress scenarios |
| **Cash flow & amortization modeling** | Loan teams specifically need payment schedules, prepayment forecasts, recovery projections | High | Partial (explicit cashflows in positions) | Needs: payment schedule generation, CPR/PSA prepayment, default/recovery modeling, adjustable-rate resets |
| **Results drilling & reporting** | Raw JSON not acceptable; risk team needs OLAP-style drill-down and export | High | Partial (cube view, summary API) | Needs: cross-cuts by issuer/sector/rating/geography, export to Excel/CSV, parameterized reports |
| **Portfolio aggregation metrics** | Dashboard needs basic portfolio health snapshot | Medium | Partial (PV sum only) | Needs: market value, book value, accrued interest, unrealized P&L, portfolio yield, WAM, WAL, concentration |
| **Run management & audit trail** | Internal firm needs reproducibility; "what was in this run?" must be answerable 12 months later | Medium | Partial (run creation, snapshot versioning) | Needs: run approval workflow, input/output versioning, calculation log, who-ran-what-when |
| **Multi-currency support** | Real portfolios have EUR, GBP, JPY loans; can't ignore FX | Medium | Partial (FX_DELTA measure exists; FX spot and scenarios exist) | Needs: multi-currency curve setup, cross-currency basis, full P&L conversion |
| **Regulatory framework (GAAP/IFRS)** | Investment firms are audited; finance team needs fair-value and ECL calculations for books | Medium | Missing | Needs: mark-to-model vs mark-to-market toggle, ECL reserve calculation, impairment triggers, GAAP/IFRS valuation differences |

## Differentiators

Features that set product apart. Not expected, but valued. Competitive advantage if done well.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Performance attribution** | "Which decisions added/subtracted value?" — tells story of portfolio management | High | Requires: benchmark definition, return decomposition (duration/spread/selection/sector), branding as insight |
| **Loan-specific analytics** | Most platforms are bond-centric; loan focus is rare and valuable | High | Include: FICO distribution analytics, geographic concentration, loan program mix, seasoning/age distribution, default probability trends |
| **Credit risk integration** | Moving beyond market risk to "what if FICO 680 cohort has 5% more defaults?" | High | Requires: PD curves by cohort, LGD estimates, concentration stress, rating migration |
| **Prepayment forecasting** | For loan teams, prepayment is THE risk; outperforms competitors who ignore it | High | Implement: CPR/PSA models, seasonal adjustments, rate-dependent prepayment, macro factors |
| **What-if rebalancing simulation** | Portfolio managers love "what if we buy/sell this position?" | Medium | Show: impact on risk metrics, new market value, tax consequences (if tracked), execution cost estimate |
| **Liquidity analytics** | "Can we liquidate 20% of portfolio in 1 week?" — increasingly important post-2023 bank stress | Medium | Include: bid/ask spread analytics by instrument type, time-to-liquidate estimates, concentration liquidation cost |
| **Seamless trade-to-settlement workflow** | Connect booking → pricing → P&L without manual steps | Medium | Integrate: trade entry, settlement confirmation, P&L reporting, exception handling |
| **Monte Carlo simulation engine** | Standard for derivatives & CVA; enables advanced scenario analysis | High | Compute: interest rate paths, macro factor paths, full portfolio revaluation, VaR/ES reporting |
| **API-first with webhooks** | Risk team needs to push results to downstream systems (RiskCache, GRC platforms, dashboards) | Medium | Provide: REST API for all operations, webhook triggers on run completion, configurable payloads |
| **Comparative analytics** | "How does this portfolio compare to peers / benchmarks?" | Medium | Implement: peer basket comparison, tracking error, benchmark decomposition, factor exposure |

## Anti-Features

Features to explicitly NOT build. Explain why to avoid scope creep.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time streaming analytics** | Thousands of positions; batch recalculation is fast enough for internal team. Real-time = 5x infrastructure cost for 2% use-case improvement. | Keep batch + intraday refresh (e.g., noon + EOD runs). Add run scheduling/automation. |
| **Multi-tenant SaaS** | Internal use only. Multi-tenant isolation = 30-50% architectural overhead. Buy vs build later if external need emerges. | Assume single-org deployment. Use role-based access (portfolio manager, risk analyst, compliance), not full tenant isolation. |
| **Pricing vendor API feeds (Bloomberg, Refinitiv)** | Licenses are expensive and lock-in is real. Firm probably has these feeds for their main book already; let their data team feed curves/spreads. | Accept market data via APIs or files; don't integrate Bloomberg/Refinitiv directly. Let firm manage vendor relationships. |
| **Full regulatory reporting (FFIEC 101, SEC N-PORT)** | Banking regulators (OCC, Fed) and SEC reporting is domain-specific, heavy, and beyond scope for internal tool. | Provide fair-value and ECL framework for firm to plug into their compliance systems. Export standardized data. |
| **AI/ML models (prepayment prediction, default prediction, anomaly detection)** | ML models are hard to maintain, expensive to backtest, and need 3+ years of data. Firm might have their own. | Use simple heuristic models (PSA, CPR tables) for MVP. Add ML hooks for v2 if firm has models. |
| **Mobile application** | Portfolio analytics requires large screens for grids/charts. Mobile = 1-2% of users, high maintenance. | Responsive web design sufficient. Educate team to use desktop. |
| **Custom trade recommendations / portfolio optimization** | Portfolio optimization (mean-variance, risk parity) is domain expertise heavy and beyond scope. Requires PM buy-in. | Provide raw analytics so PM can make decisions. Don't recommend. |
| **Commodity/FX spot trading analytics** | Loan book is core; spot commodities/FX trading is distraction. Different risk model. | Support FX hedging (FX forwards, swaps) for the portfolio, not commodity speculation. |

## Feature Dependencies

Graph of what depends on what. Affects phase ordering.

```
Market Data Ingestion
  ↓
  ├─→ Pricing Engine (needs curves, spreads)
  │     ├─→ Loan Pricer
  │     ├─→ Bond Pricer
  │     ├─→ ABS/MBS Pricer
  │     ├─→ Derivatives Pricer
  │     └─→ Instrument Master (instrument definitions)
  │
  ├─→ Risk Measures (needs pricing results)
  │     ├─→ Market Risk (DV01, duration, convexity)
  │     ├─→ Credit Risk (PD, LGD, rating migration)
  │     └─→ Liquidity Risk (spreads, concentration)
  │
  ├─→ Scenario Management (needs market data, pricing engine)
  │     ├─→ Shock scenarios (rate bumps, spread shocks)
  │     ├─→ Historical stress scenarios
  │     └─→ Monte Carlo paths
  │
  └─→ Results Aggregation (needs pricing + risks)
        ├─→ Portfolio metrics (market value, accrued, P&L)
        ├─→ Drill-down analytics (by issuer, sector, rating)
        ├─→ Performance attribution (needs benchmark)
        └─→ Reports & export

Portfolio Management
  ├─→ Portfolio hierarchy
  ├─→ Position tracking
  ├─→ Holdings import
  └─→ Historical snapshots

Trade Lifecycle
  ├─→ Booking (creates position)
  ├─→ Amendment (updates instrument terms)
  └─→ Termination (ends position)

Regulatory Framework
  ├─→ GAAP/IFRS valuation support
  ├─→ ECL modeling
  └─→ Audit trail
```

## MVP Recommendation

**Phase structure should prioritize:**

1. **Core Valuation** (P1) — Get institutional-grade pricing for all asset types
   - Instrument master with loan/bond/ABS/MBS/derivatives definitions
   - Pricers: floating-rate, callable/putable, ABS/MBS, swap/swaption
   - Market data: multi-curve setup, spreads, validation
   - Measures: DV01, spread duration, OAS, YTM, clean/dirty price

2. **Portfolio Analytics Foundation** (P2) — Enable core workflows
   - Portfolio hierarchy and node management
   - Holdings import and aggregation
   - Cash flow modeling (payment schedules, prepayment, default/recovery)
   - Scenario management (user-defined scenarios, shock combinations)
   - Results drilling (OLAP cube, by issuer/sector/rating/geography)

3. **Risk & Regulation** (P3) — Address risk team and compliance needs
   - Market risk: key-rate duration, convexity, VaR, ES
   - Credit risk: PD modeling, rating migration, concentration stress
   - Liquidity risk: bid/ask spread analytics, liquidation time
   - GAAP/IFRS valuation framework
   - ECL modeling

4. **Loan-Specific Advantage** (P4) — Differentiate
   - FICO/LTV distribution analytics
   - Geographic concentration
   - Prepayment forecasting
   - Loan program decomposition
   - Seasonal adjustment models

5. **Advanced Analytics & Integration** (P5) — Polish
   - Performance attribution
   - What-if rebalancing simulation
   - Monte Carlo simulation engine
   - API-first design with webhooks
   - Comparative analytics (peers, benchmarks)

**Defer to v2:**
- Real-time streaming
- Multi-tenant SaaS
- Vendor API feeds (Bloomberg, Refinitiv)
- Full regulatory reporting
- ML-based prepayment/default models
- Mobile app

## Key Feature Interactions

### Loan Teams Workflow
```
Upload positions
  → System fetches instrument master (loan coupon, amort schedule)
  → Ingests market data (OIS curve, loan spread curve)
  → Calculates PV, accrued interest, DV01, spread duration
  → Applies scenarios (parallel rates +1bp, spreads +25bp, prepayment -10%)
  → Aggregates by geography, FICO, loan program
  → Risk team sees: concentration heatmap, prepayment risk, rate sensitivity
  → Portfolio manager rebalances based on what-if analysis
```

### Risk Team Workflow
```
Run portfolio valuation at EOD
  → Get PV, market value, accrued interest snapshot
  → Apply stress scenarios (2008 financial crisis, COVID-2020, recent Fed shock)
  → Calculate VaR / Expected Shortfall
  → Flag concentration issues (top 10 issuers, geographic concentration)
  → Generate report for chief risk officer
  → Export to risk reporting system (RiskCache, Numerix, etc.)
```

### Compliance Workflow
```
Quarter-end valuation
  → System calculates fair value (mark-to-model for illiquid loans)
  → ECL reserve calculation (expected loss under IFRS 9 / CECL)
  → GAAP/IFRS reconciliation
  → Audit trail: input data, methodology, approvals
  → Export to financial reporting system
```

## Source Materials

**Institutional portfolio analytics platforms studied (training data + codebase context):**
- Aladdin (BlackRock) — portfolio and risk analytics for institutions; benchmarks for feature breadth
- Bloomberg PORT — fixed income analytics, risk measures, scenario modeling
- Moody's Analytics — credit risk and default modeling
- MSCI RiskMetrics — VaR, factor models, attribution
- Numerix — derivatives and structured products

**Domain knowledge:**
- Fixed income asset allocation and portfolio management (Fabozzi, Marks)
- Loan portfolio analytics and credit risk (Altman, Kealhofer)
- Regulatory frameworks (GAAP, IFRS 9, Basel III)
- Market data: multi-curve framework, OIS/Libor fallback

**Project context:**
- Existing MVP: loan/bond/FX pricers, scenario application, results aggregation
- Risk team requirements: portfolio analytics with loan focus, regulatory compliance
- Investment firm constraints: lighter than banking regulation, internal use only

