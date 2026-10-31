# Deploy Indian Market Lab as one public website

**No brokerage account or static IP needed.** The public website is for educational research, not trading. The Streamlit site needs access to the unofficial Yahoo chart endpoints to display research quotes; providers can rate-limit or block it.

## 1 — Preview on your computer

Double-click `OPEN_DASHBOARD_DEMO.html`. This is a safe, fully offline view with **fabricated** stock prices. It cannot receive real market data.

## 2 — Deploy the data-enabled version to your own website URL

1. Create a new GitHub repository named `indian-market-lab-web` (do not use the Ashok Enterprise business repository).
2. Upload the files from this package to the repository root.
3. Keep the project repository free of access tokens, `.env` files, personal CSV files and credentials.
4. Go to https://share.streamlit.io/ and sign in with GitHub.
5. Select **Create app**, choose the repository and branch, and enter the main file path: `web_dashboard.py`.
6. Click Deploy. Streamlit creates a shareable URL ending in `.streamlit.app` that you can bookmark or link to from your portfolio.

### Provider warnings

- If the free Streamlit service is sleeping/throttled, the website may take time to start or stop responding.
- Free Yahoo Finance chart endpoints are unofficial and may decline requests from cloud networks; the UI displays errors instead of silently replacing quotes with synthetic data.
- For predictable execution-quality or real-time updates you would need a properly licensed data service; no broker is integrated here.
- This app has **no login or private database**. The paper journal is kept in the current viewer's Streamlit session only; exporting before closing is recommended.

## 3 — Local data-enabled website

On Windows double-click `START_WEBSITE.bat` in the **full project ZIP**. This automatically starts the server and opens http://localhost:8501 on your PC. If you want the single website accessible from other devices, deploy via Streamlit in step 2.

## Troubleshooting

- Python not found: Install Python 3.11+ from https://www.python.org/downloads/ and enable Add Python to PATH.
- Streamlit installation failed: Check your internet access and run `python -m pip install -r requirements.txt` manually.
- HTTP 429 / HTTP 403: Yahoo has refused the data request. Wait, reduce stock count, or use a licensed feed; don't use it for real-time order decisions.
- Demo chart looks different from NSE: Expected. Demo data is **synthetic**.

Official Streamlit hosting instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy