# Indian Market Lab — Research Intelligence Edition

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