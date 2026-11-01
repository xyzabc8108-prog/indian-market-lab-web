# Indian Market Lab — division-based full-stack application

This repository keeps the previous Streamlit `web_dashboard.py` **unchanged**, and adds a separate **FastAPI + modular JavaScript frontend** website under `fullstack/`.

## Separate sections, not one dashboard

| URL | Section | Function |
|---|---|---|
| `/#/home` | Home | Overview and section navigation |
| `/#/stocks` | Stock Research | Automatic symbol lookup, historical trends, ATR entry/stop/target, ₹50,000 paper budget / 1% risk |
| `/#/scanner` | Market Scanner | Import dated NSE equity CSV/UDiFF ZIP prices and calculate transparent rankings |
| `/#/indices` | Indices Explorer | Index directory and **known** optional provider mappings |
| `/#/derivatives` | F&O Planner | Long CE/PE and illustrative long-future risk sizing using verified user inputs |
| `/#/news` | News Intelligence | RSS headlines and possible sector relevance, without directional forecasts |
| `/#/paper` | Paper Portfolio | Browser-local, hypothetical-only journal and calculation tool |
| `/#/about` | Data & Settings | Data limitations, API status and product rules |

The frontend is plain modular JavaScript, HTML and CSS (no build step), served by the FastAPI backend on the **same origin**. API endpoints are read-only for prices and news; only local research calculations and upload processing are posted. There is **no real brokerage, account, authentication, order placement, automated trade or live exchange data feed**.

## Local startup

At the GitHub repository root:

```bash
python -m pip install -r fullstack/backend/requirements.txt
python -m uvicorn fullstack.backend.main:app --reload
```

Open `http://localhost:8000` (API docs: `/docs`, health: `/api/health`).

## Full-stack deployment with Render

The repository includes a root-level `render.yaml` that specifies a Python free-tier web service. Render offers free testing services but these can sleep, restart, and rate-limit external requests. Availability and pricing may change.

1. Sign in at https://dashboard.render.com/ with GitHub.
2. Choose **New → Blueprint**, select `xyzabc8108-prog/indian-market-lab-web` and `main`, then approve the service defined in `render.yaml`. Alternatively choose **New → Web Service** and configure:
   - Build command: `pip install -r fullstack/backend/requirements.txt`
   - Start command: `uvicorn fullstack.backend.main:app --host 0.0.0.0 --port $PORT`
   - Instance: Free, if available.
3. Wait for Render to report a healthy deployment and open the assigned `*.onrender.com` address.
4. Visit `/api/health`, then use dedicated pages from the left navigation.
5. Your existing `https://indian-market-lab-rohan.streamlit.app/` is **not** replaced by this deployment; it remains the original Streamlit site. You can eventually redirect to the new site after verifying it.

**No Render deployment has been performed automatically.** This repository commit supplies deployable application code; a separate service must be created in the user's Render account.

## Data integrity and privacy

- NSE reference directory is fetched on demand, when available. A small fallback list is labelled as incomplete. **The user-uploaded NSE.zip is not republished.** Stock tickers can also be entered manually.
- Price history is requested only for the selected symbol from an **unofficial** Yahoo Finance chart endpoint. Data may be delayed, blocked, or stale; a failed request produces an error, not fabricated prices. Verify with authorized sources and the data provider's terms.
- Market scanner requires **real dated OHLCV** history and at least 60 sessions per stock; a securities-directory ZIP cannot substitute for market prices. Scores are descriptive, not calibrated predictions.
- News is retrieved on demand from public RSS feeds, may be unavailable, and is not a trading signal.
- F&O products require user-entered verified lot size, premium, strike, spot, expiry and/or margin; the app does not retrieve a live options chain.
- Paper Portfolio uses each browser's local storage. **There is no authentication or secure multi-user database** yet; don't use it for private financial account information.
- The site has no automatic real orders, backend-saved trades, or broker credentials.
- Paper risk uses a default ₹50,000 capital, 1% planned risk (₹500), and 25% maximum single-stock cash allocation (₹12,500). Actual gap fills and costs can exceed planned losses.

## Offline checks

```bash
python -m pytest -q fullstack/backend/tests/test_api.py
node --check fullstack/frontend/app.js
```

Production improvements after user acceptance: dedicated licensed market-data access, auth and secured user database, persistent paper journal, caching/rate controls, corporate-action handling, test automation, usage monitoring and external deployment verification.
