# New: Indian Market Lab — Modular Full-Stack Website

A separate division-based site is now available in [`fullstack/`](fullstack/). It has individual pages for Home, Stock Research, Market Scanner, Indices, F&O Planner, News Intelligence, Paper Portfolio, and Data & Settings. Frontend: modular HTML/CSS/JavaScript; backend: FastAPI. No real orders.

**[Full-stack deployment instructions](FULLSTACK_DEPLOY.md)** · [Backend code](fullstack/backend/main.py) · [Frontend code](fullstack/frontend/app.js) · [Automated tests](fullstack/backend/tests/test_api.py)

**Hosting status:** The full-stack source is committed, but the separate Render web service is not deployed yet. The existing [Streamlit prototype](https://indian-market-lab-rohan.streamlit.app/) remains unchanged. To publish the new site, deploy the root `render.yaml` Blueprint in your own Render account.

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
