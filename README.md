# PUBLIC DEPLOYMENT SAFETY STATUS — 3 NOVEMBER 2026

**Streamlit prototype (owner-only private access):** The `indian-market-lab-rohan.streamlit.app` entrypoint
is now configured to show **only a synthetic educational sandbox** by default
(Step 21.21.7). Public named-stock quotes, the original Auto Stock Assistant,
trade-level suggestions, stock backtests and unofficial Yahoo data requests are
**disabled**. It offers a synthetic line-chart example and manual virtual
risk-budget arithmetic. [Technical controls](STREAMLIT_SAFETY.md).

**Render full-stack site:** https://indian-market-lab-fullstack.onrender.com
has Market Data Safety Mode active (Step 21.21.2). Public Yahoo-derived
prices and stock-specific terminal scenarios are blocked; public
uploaded-price scanner inputs are also blocked by default (Step 21.21.9).
The public scanner now demonstrates descriptive indicators exclusively on
fictional internally generated sequences; manual budgeting remains available.
The full-market scanner research engine is retained for future authorized
private/reviewed use. Beta registrations, feedback, payments and brokerage
orders remain disabled.

**Important:** Older README sections below document historical code and
features, **not current public functionality or legal approval**. See
[scanner restrictions](MARKET_DATA_SAFETY.md) and
[Streamlit restrictions](STREAMLIT_SAFETY.md). Do not
reactivate price feeds merely to restore the old interface. A valid provider
agreement and professional regulatory review are required before deciding
which functions may safely become public.

---

## Trader Mode — full-screen chart workspace

Open **https://indian-market-lab-fullstack.onrender.com/terminal** or use the
**Trader Mode** switch in the full-stack site header. The exit switch returns
to the normal research pages.

- Search the available NSE equity directory by symbol/company; paginate the
  public directory when available. A limited fallback is clearly labelled
  if NSE blocks server-side directory requests.
- Choose 1-minute, 5-minute, 15-minute, hourly, daily or weekly candles with
  compatible historical ranges. Unavailable combinations produce an error.
- Interactive candles, volume, and optional SMA20, SMA50 and EMA20 overlays.
- A reference library of 27 common candlestick and chart patterns, plus
  transparent heuristic *candidates* detected in recent candles. This is not
  every chart pattern worldwide, and no candidate implies a validated signal.
- Illustrative lower/middle/upper outcomes from 2,500 resampled historical
  paths for a user-selected 5, 10, 20 or 40 future candles.
- Clearly separated past candles and future scenarios. **No calibrated future
  prediction, live exchange feed, broker login or real orders.**
- Prices are requested from unofficial Yahoo Finance historical chart endpoints
  and may be delayed, unavailable or subject to provider rate limits.
- Chart engine: TradingView Lightweight Charts™ (Apache 2.0); attribution and
  link are displayed in the terminal footer.

Offline terminal tests: `python -m pytest -q fullstack/backend/tests/test_terminal.py`.
GitHub Actions workflow: `.github/workflows/trader-terminal-tests.yml`.

# New: Indian Market Lab — Modular Full-Stack Website

A separate division-based site is now available in [`fullstack/`](fullstack/). It has individual pages for Home, Stock Research, Market Scanner, Indices, F&O Planner, News Intelligence, Paper Portfolio, and Data & Settings. Frontend: modular HTML/CSS/JavaScript; backend: FastAPI. No real orders.

**[Full-stack deployment instructions](FULLSTACK_DEPLOY.md)** · [Backend code](fullstack/backend/main.py) · [Frontend code](fullstack/frontend/app.js) · [Automated tests](fullstack/backend/tests/test_api.py)

**Hosting status:** The Render full-stack service is live with Market Data Safety Mode. The Streamlit prototype has a separate fail-closed synthetic-only safety guard. Refer to [market-data restrictions](MARKET_DATA_SAFETY.md) and [Streamlit safety](STREAMLIT_SAFETY.md) before interpreting the historical feature descriptions below.

---

# Indian Market Lab — Research Intelligence Edition

## New: Auto Stock Assistant — simplest way to use this website

1. Open https://indian-market-lab-rohan.streamlit.app/ and select **🔎 Auto Stock Assistant** (first tab).
2. Start typing the name of a company (for example, Infosys) and select a suggested entry, or type its exact NSE ticker (such as `INFY`) and press Enter.
3. Available daily historical data is requested automatically. When the provider responds, the page shows indicators, historical trend evidence, reasons for and against a potential setup, and an illustrative cash-only paper entry/stop/target plan.
4. The standard assumptions are **₹50,000 capital, 1% planned risk (₹500 maximum) and a 25% (₹12,500) allocation cap**. Change these only inside the optional budget expander.
5. If prices are missing, invalid or stale, the page tells you; it does **not** substitute invented quotes. The `WAIT / NO-TRADE` state is a normal valid outcome.

This assistant uses a cached NSE symbol directory when the exchange download works, with a clearly labeled partial fallback and manual ticker entry when blocked. It uses the existing unofficial Yahoo historical chart source, **not** exchange-authorized real-time prices. Its 2,000 historical-resampling paths are model scenarios, not calibrated future event probabilities. Positions are cash-long examples only; no futures/options orders or real trades are placed.

Browser-hosted Indian market research toolkit for **education and paper trading only**. No brokerage account, credentials, order-placement API, or paid/static-IP infrastructure required.

**Website:** https://indian-market-lab-rohan.streamlit.app/  
**Source:** https://github.com/xyzabc8108-prog/indian-market-lab-web  
**Entry point:** `web_dashboard.py`

## New research modules

- **Stock Decision Lab:** Search by NSE ticker or supported common company name; explain SMA20/SMA50, 14-period ATR, RSI, price momentum, 20-day high/low, hypothetical ATR entry/stop/target reference levels, favorable and risk considerations.
- **Scenario Engine:** 1,000–100,000 historical-bootstrap paths over 1–60 daily bars. Reports the modeled path frequencies of stop-first, target-first, neither, scenario return distribution and tail losses. They are **not probabilities of real future events**. Assumes independent daily-return sampling, fixed levels and daily closing-price barrier checks.
- **1,000 Setup Explorer:** Tests 10 ATR stops × 10 reward multiples × 10 horizons on 2,000 shared simulated paths = 2 million configuration/path comparisons. Exports complete table. Rankings are **in-sample and susceptible to selection bias**; not optimized/validated trading signals.
- **Budget Desk:** Cash-long share sizing from total capital, planned risk-per-trade, max allocation, estimated fees and slippage, with a daily loss budget.
- **F&O Desk:** Long call/put maximum premium-at-risk sizing, expiry breakeven, and an illustrative long futures margin/exposure/stop planner. Current premium, strike, expiry, lot size and margin are **user-entered** and must be checked against live exchange/broker information. Short/naked option positions are **not included**.
- **News Radar:** On-demand Google News RSS headlines grouped by Indian market topic, date/source links, and transparent headline keyword mapping to *potentially related* NSE sectors/stocks/indices. No news-derived predictions or claims of price causation. Official NSE/SEBI/RBI verification links.
- **Own data:** Optionally import a daily OHLCV CSV for stock/scenario analysis when public chart services are inaccessible.

All original tabs (watchlist, charts, screener, SMA backtest, risk planner and paper journal) remain present.

## Data sources and caveats

- **Synthetic demo** is the default. Demo OHLCV is invented for UI and testing purposes only.
- Yahoo Finance research data is **unofficial, can lag, can be unavailable or blocked on cloud networks, and is not guaranteed accurate for execution**. Verify source, as-of time, stock splits, dividends, trading sessions and current price separately.
- The news RSS feed depends on an unauthenticated third-party provider and may be throttled or unreachable. The software displays an error instead of inventing headlines.
- A stock's name in a headline does not prove it will move, let alone its direction. Sector links are hypotheses based on words in titles, not return correlations.
- Scenarios/strategies may look accurate through overfitting; do walk-forward/out-of-sample validation, account for Indian brokerage/fees/taxes, expiry/liquidity and corporate actions. No system can enumerate all market possibilities or guarantee entries/exits.
- **F&O carries substantial risk.** NSE lot sizes, expiry rules and margins change. The F&O calculator is an educational manual-entry planner, not a contract selector or margin validator. Long futures can lose **more than margin** and a long option can lose the **full premium**.
- Fixed-risk stop levels may gap/execute badly; risk caps are planned limits, not loss guarantees.
- Public Streamlit instances have resource quotas. Simulations are capped at 100,000 paths per run.
- Session-based paper journal is not permanently stored. Export CSV before leaving.

## Deploy / update

On Streamlit Community Cloud: app `indian-market-lab-rohan`, repository `xyzabc8108-prog/indian-market-lab-web`, branch `main`, entrypoint `web_dashboard.py`.

Python packages are installed from `requirements.txt`. Streamlit normally rebuilds after a GitHub push. If not, use the Streamlit app menu to reboot/redeploy.

Run locally:

```bash
python -m pip install -r requirements.txt
python -m streamlit run web_dashboard.py
```

Pure model tests:

```bash
python -m unittest -v test_research_engine.py
```

## Reference checks

- [NSE derivatives contract information](https://www.nseindia.com/static/products-services/equity-derivatives-contract-information)
- [NSE contract specifications](https://www.nseindia.com/static/products-services/equity-derivatives-contract-specifications)
- [NSE announcements RSS](https://www.nseindia.com/static/rss-feed)
- [SEBI FY25–FY26 individual derivatives trader study](https://www.sebi.gov.in/reports-and-statistics/research/aug-2026/study-profitability-of-individual-traders-in-the-equity-derivatives-segment-fy25-fy26-_103835.html)
## NSE stock directory, indices and historical market replay

Open the **All Stocks & Indices** tab and select **Load directory and market tools**.
- The site attempts to load NSE's official listed-equities CSV (daily-cached). If the exchange blocks Streamlit Cloud, download it from https://www.nseindia.com/static/market-data/securities-available-for-trading and upload the CSV in the app. The built-in emergency sample is **not** all listed stocks.
- Browse a representative index-name directory and optionally import a larger one. Only some indices have mapped Yahoo provider tickers; unverified mappings do not create prices.
- For **one selected instrument**, optionally recheck unofficial Yahoo 5-minute historical research bars every 5 minutes **while that browser session is active**, showing the bar's timestamp, age, and source. This is **not guaranteed exchange-real-time**.
- Paper-trade replay reveals historical candles up to a selected cursor, applies a fixed capital risk budget, and reports stop/target outcomes. It never places orders.
- Import an **NSE EOD CSV** to screen a whole-market end-of-day snapshot without thousands of quote calls. This is not a live full-market screener.
- Run pure-module tests with `python -m unittest test_market_universe.py` (where test file is present).

**Data licensing:** Public real-time streaming or widespread redistribution of NSE quotes normally requires an authorized market-data arrangement. The site does not have one. Official policy: https://www.nseindia.com/static/market-data/nse-data-policy


## Phase 1 — Full-Market Scanner

Open the **Full-Market Scanner** tab on https://indian-market-lab-rohan.streamlit.app/ to import NSE EQ cash-market daily histories and rank stocks with a transparent six-component 0–100 descriptive indicator score. The defaults are ₹50,000 paper capital, 1% (₹500) risk per idea and a 25% (₹12,500) single-stock cash allocation cap.

- Upload `NSE.zip` as the reference equity universe, plus **at least 60 real EOD sessions per stock** in CSV or CM-UDiFF ZIP archives; universe symbols alone cannot produce technical signals.
- Validate OHLCV, date freshness, duplicates and history coverage before interpreting rankings.
- Inspect reason codes and idealized 2×ATR stops / 2R targets; these are not order prices, probabilities, or buy recommendations.
- See [full instructions](README_FULL_MARKET_SCANNER.md), [offline tests](test_full_market_scanner.py) and the GitHub Actions scanner-test workflow.

The full-market feature is historical EOD, not licensed exchange real-time. Actual coverage depends on imported price data and may be incomplete. The public app does not execute orders.
