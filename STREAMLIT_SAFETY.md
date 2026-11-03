# Step 21.21.7 — Original Streamlit App Safety Mode

Scope: https://indian-market-lab-rohan.streamlit.app/
Source entrypoint: web_dashboard.py
As of: 3 November 2026

## Why this matters

The independent Streamlit prototype previously fetched unofficial Yahoo Finance
price data. Its automatic stock assistant and other tabs contained named-stock
indicators, paper entry/stop/target examples and historical scenarios.
The full-stack Render site's Market Data Safety Mode does not secure
this separate Streamlit entrypoint.

## Default public behavior (fail closed)

The Streamlit entrypoint now imports the safety module immediately after
Streamlit page configuration. If public data is not explicitly approved,
render_safety_mode() displays only a separate Streamlit page, and
st.stop() halts before legacy functions or widgets are defined.

The public page has:
- A prominent Market Data Safety Mode notice.
- A fully synthetic, reproducible, explicitly fictional index illustration.
- A user-entered virtual capital/risk/allocation budget calculator.
- Official regulatory links and the live Render research site.
- No Yahoo, NSE or quote API calls.
- No real-company quote or chart outputs, no target/stop recommendations,
  no automatic stock analysis, no order execution, and no public signup.

The previous Streamlit functions remain in repository history and source for
future refactoring; they cannot execute through the default public entrypoint.
The legacy history() wrapper has a second direct-access guard against
price-provider calls whenever safety mode is active.

## Reversibility — currently NOT authorized

Two server-only environment variables must BOTH be set to true
to unlock the legacy view:

- IML_STREAMLIT_PUBLIC_PRICE_ENABLED
- IML_STREAMLIT_DATA_RIGHTS_APPROVED

Both are absent by default. They must remain unset or false.
The presence of these variables does not prove a licence.
Do not enable either variable to restore the old Yahoo Finance source.

Before planning any release of price-based tools:
1. Obtain written permission covering data display, caching and derivatives.
2. Replace the unofficial data provider with an authorized implementation.
3. Review the RA/IA/educational classification of each named-stock output.
4. Reassess the public upload scanner for rights and advisory concerns.
5. Add tests verifying that the authorized provider and relevant constraints
   are actually enforced.

A safe rollback is to keep both flags unset; do not revert to an old commit
that publicly exposes the unlicensed provider.

## Testing and verification

Run: python -m unittest -v test_streamlit_market_safety

GitHub Actions .github/workflows/scanner-tests.yml runs the safety tests
with the scanner's offline tests when either relevant code path changes.

After the linked Streamlit deployment updates, visit the Streamlit URL in
a fresh browser/private window and verify:
- The title and MARKET DATA SAFETY MODE are clearly displayed.
- Only four safe tabs are shown.
- The synthetic index says fictional, not a real NSE security.
- Manual risk for Rs. 50,000 and 1 percent is Rs. 500.
- No Auto Stock Assistant, named-stock price chart, Yahoo option or
  stock-specific entry/stop/target is offered.

Note: A successful CI run and a new source commit are not themselves proof
that Streamlit Community Cloud has finished deploying the change.
