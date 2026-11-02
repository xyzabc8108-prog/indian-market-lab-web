# Indian Market Lab — Beta Legal & Trader UX Audit (2 November 2026)

## Completed in repository

- Rewrote /privacy and /terms into public-facing copy, removed internal development notes and placeholder warnings, used "2 November 2026" dates.
- Named Render as host and unpkg CDN as supplier of the TradingView Lightweight Charts script; indicated technical requests may expose visitor IP/request metadata to providers.
- Unified Trader Terminal's exit and modal return links to /#/home.
- Confirmed UI dynamically restricts chart history by candle interval and backend validates the same allowlist. 1-minute candles only allow 1d or 5d lookback.
- Removed the duplicate Market Watch loading message; added 30–45 second request timeouts, retry UI, and an *in-memory browser-session* last-successful-snapshot fallback. It never fabricates candles.
- User-editable virtual capital, risk percentage and hypothetical stop distance; risk estimate and example quantity are computed from user inputs, not orders.
- Renamed P10/P50/P90 scenarios to historical resampling bands; kept symbols illustrative, not asserted price predictions. A neutral label does not automatically change legal status.
- Trader Mode risk acknowledgment was **already** stored in localStorage with a versioned key; existing function verified unchanged.
- Removed automated security-specific entry/stop/target/quantity fields from the public stock research API and replaced page with descriptive indicators and virtual budget. The separate user-entered paper portfolio and statistical band outputs still exist.
- Updated regression tests and CI command to cover the updated public routes and API contracts.
- Bumped asset version strings for browser refresh.

## Still blocked before collecting visitor emails or enabling payments

1. **Operator name and grievance/privacy contact:** No verified legal entity/owner identity or working email has been provided. Never invent these. Beta interest and feedback forms remain closed until contact details, deletion processes and dedicated storage are verified.
2. **Specific city jurisdiction:** A specific city or exclusive jurisdiction requires actual operator and legal advice; public Terms use competent Indian courts without inventing a venue.
3. **SEBI and market-data compliance:** SEBI circular dated **8 May 2026**, effective **1 July 2026**, changed covered educational market-price usage lag from 3 months to **30 days**: https://www.sebi.gov.in/sebi_data/attachdocs/may-2026/1778242522289.pdf . The current site **does not enforce a fixed uniform 30-day delay**. Historical candle timestamps and age are shown; it must not be marketed as compliant merely because the Terms disclaim advice. Stock-specific simulation percentiles and current quote sources still need a professional product/legal and provider licensing review. Intraday price histories from the public Yahoo endpoint are not covered by an independently verified redistribution licence.
4. **Testing/deploy:** GitHub code presence and browser JS syntax checks were verified. Complete GitHub Actions test run and new Render deployment must be checked for the final commit; an automated test is not a legal review.
5. **Long-term fallbacks:** Browser-session snapshot fallback is memory-only. It is lost on reload; storing/redistributing historical provider data requires licensing and a compliant storage design.

## Launch recommendation

Keep public beta as free, read-only educational research; keep live/premium signups disabled. Confirm data rights, operator details and the correct regulatory category before adding commercial offers. If the platform is intended to operate as solely educational using named-security price data, investigate applying the current 30-day requirement and how this affects or disables short intraday intervals. Do not claim the site has a 30-day data delay until actually implemented and tested.

No user accounts, broker order execution, or data-storage credentials were added during this audit.
