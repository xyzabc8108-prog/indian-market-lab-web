# Indian Market Lab — Market Data Safety Mode (Step 21.21.2)

## Reason and default
Indian Market Lab's current public-price research originally fetched unofficial
Yahoo Finance OHLC for Indian stocks and intraday charts. No public-display or
redistribution licence has been verified for that source. Disclaimers and a
research-only label do not themselves grant rights or establish SEBI compliance.

**The price-data safety mode is ON by default**, even when the server has no
special environment configuration. A new release must never inadvertently
resume unofficial public price delivery.

## What is blocked while safety mode is ON

- `GET /api/stock/{ticker}/analysis`: HTTP 503, safe explanation.
- `GET /api/stock/{ticker}/history`: HTTP 503, no price bars.
- `GET /api/terminal/{ticker}`: HTTP 503, no candlestick OHLC,
  trend indicators, historical pattern-derived output, or simulations.
- Cache reads and calls to the unofficial price provider are blocked *before*
  any public response. No previously cached data is replayed when the mode
  is active.
- The live NSE equity directory fetch is replaced by an offline illustrative
  symbol list during safety mode.
- The website and Trader Terminal display understandable notices rather than
  fabricated prices, indefinite loading placeholders, or unlicensed snapshots.

## What continues to work

- `/api/market-data/status`: public capability state, no secret values.
- Stock search using offline example symbols.
- `/api/indices`: directory/reference labels only (no live price data).
- `POST /api/scanner/import`: HTTP 503 in the public default safety mode,
  blocked before uploaded CSV/ZIP bodies are parsed.
- `GET /api/scanner/demo`: runs the existing indicator engine on two
  completely fictional internally generated price sequences, omitting actual
  symbols, real prices, trade recommendations and entry/stop/target outputs.
- `GET /api/scanner/status`: reports server-side public-upload gate state,
  without revealing configuration secrets. Private/offline scanning code is
  retained for authorized research. Uploaded-file use is not automatically
  licensed merely because the user supplies the file.
- `POST /api/risk/plan`, `POST /api/derivatives/plan`: manual input
  hypothetical calculations without broker feeds.
- News links, browser-local paper journal, legal pages, privacy inquiries.
- Public beta waitlist and feedback remain DISABLED, with
  `BETA_PRIVACY_READY=false`. No real orders, accounts or payments.

## Reversibility — deliberate and operator-controlled

Price endpoints are enabled only when **BOTH** server environment flags are
explicitly `true`:

- `IML_PUBLIC_PRICE_DATA_ENABLED=true`
- `IML_MARKET_DATA_LICENSE_APPROVED=true`

Never set these flags just to remove the UI banner. They must remain unset or
`false` until the operator has independently confirmed a valid data-provider
agreement covering **each required market, resolution, display and derived
usage**, and has obtained a product-specific review of applicable SEBI, NSE,
exchange and provider conditions. The flags are an operational guard, not
proof of licensing or regulatory approval.

**IMPORTANT:** Re-enabling the existing Yahoo-based source using these flags
does not transform that unofficial source into a licensed feed. For an approved
production source, implement provider replacement and validate its contract
before enabling the switch. Reversing the gate alone is NOT approved.

No public button, query parameter or account can control these environment
flags. The current default is the safe fallback even if only one flag is true.
A service restart/redeploy applies Render environment changes.

## Verification

Run the project's Python tests, including
`fullstack/backend/tests/test_market_data_safety.py`. The tests use mocked
prices to exercise the previously supported mathematical paths; tests never
contact real price providers.

On the deployed instance verify:
- `GET /api/market-data/status` reports
  `market_data_safety_mode:true, public_price_data_available:false`.
- Historical stock analysis, history and terminal price routes return HTTP 503
  and do not include any OHLC data or scenario results.
- Synthetic scanner demonstration, manual risk calculator, paper journal,
  news and legal pages remain usable. Public price-file import is blocked.
- `GET /api/beta/status`: both `waitlist_open:false` and
  `feedback_open:false`.
- `GET /api/health`: `real_orders:false`.

This safety feature is not a substitute for a provider licence or legal
evaluation. Do not present the beta as fully release-compliant solely because
the public price endpoints are blocked.

## Public scanner safety (Step 21.21.9)

Default: real-price CSV/ZIP imports are OFF, independent of the separate
Yahoo/terminal price gate. The browser has no public upload form by default,
and the API returns HTTP 503 **before parsing multipart bodies**.

Public scanner uploads may only be unlocked after both server-only flags are
true, and only after independent rights/SEBI legal review of the implementation:
- `IML_PUBLIC_SCANNER_UPLOAD_ENABLED=true`
- `IML_SCANNER_COMPLIANCE_APPROVED=true`

Keep both unset. Neither flag proves permission, and uploading an NSE file
does not by itself authorize public analytics or redistribution. Never turn
these flags on just to restore the previous scanner UX.

The new educational demo is deterministic, using fabricated DEMOA and DEMOB
sequences. No live/real/securities market data, real issuer names, trade
entries, share quantities, stops or targets are sent in its response.
Test this with the repository safety tests and inspect the production UI.
