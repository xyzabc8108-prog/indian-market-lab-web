# Indian Market Lab — NSE Research Dashboard

A browser dashboard for **Indian-market research and paper trading**, hosted using Streamlit. No brokerage account, reactivation, static IP or Oracle Cloud instance is required.

**Project is read-only. It never places real orders.**

## Launch on Streamlit Community Cloud

1. Open https://share.streamlit.io/ and sign in using GitHub.
2. Create a new app from the repository `xyzabc8108-prog/indian-market-lab-web`.
3. Set **branch** to `main` and **main file path** to `web_dashboard.py`.
4. Choose a public app URL and click **Deploy**.
5. Streamlit installs packages from `requirements.txt`.

This GitHub repository **does not itself host a running Streamlit server**; the Streamlit deployment step is required for a working public website.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run web_dashboard.py
```

Then open `http://localhost:8501` in your browser.

## Features

- NSE watchlist for up to eight stocks, INR prices and IST timestamps
- Research charts and historical CSV exports
- Simple moving-average screener and hypothetical SMA backtesting
- Long-only risk/position-size planner
- Session-only paper-trade journal, with CSV export
- Offline synthetic demo mode (clearly labeled as fabricated)
- Optional unofficial Yahoo Finance chart data (broker-free)

## Important data limitations

- The dashboard defaults to **synthetic demonstration mode**, not live trading data.
- Yahoo Finance chart requests use an **unofficial** public endpoint. Quotes can be delayed, unavailable, throttled or blocked on cloud servers and are **not exchange-verified real time**.
- If the provider fails, the app shows an error rather than silently substituting demo data.
- Paper results are hypothetical and omit slippage, taxes, full fee schedules and corporate-action adjustments. They are not predictions of future returns.
- There is no broker order or credentials integration.
- Journal data lives in the current viewer's Streamlit session; use CSV export to save it.
- Do not upload API secrets or sensitive personal trade data to this public repository.

## Offline UI preview

Open [OPEN_DASHBOARD_DEMO.html](OPEN_DASHBOARD_DEMO.html) locally to see a static browser preview. It uses fabricated data and is not the live Streamlit website.

## Status

Source is committed to GitHub. Hosting must be activated separately on Streamlit Community Cloud.
