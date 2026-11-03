# Step 21.21.10 — Third-party licence and attribution audit

Date: 3 November 2026. Scope: public Indian Market Lab Render app.

This is a software/content provenance review, **not an opinion that all
licensing or regulatory questions have been resolved**.

## TradingView Lightweight Charts — attribution repaired

- Publisher: TradingView, Inc.
- Library: Lightweight Charts (open-source chart renderer; not a data feed).
- Governing licence: Apache License, Version 2.0.
- The upstream README requires the NOTICE and a visible TradingView link.
- Upstream NOTICE verified at:
  https://github.com/tradingview/lightweight-charts/blob/master/NOTICE
- Upstream full Apache licence:
  https://github.com/tradingview/lightweight-charts/blob/master/LICENSE
- This application now displays the upstream two-line NOTICE in the
  Trader Terminal footer and on /third-party-licenses, with an external
  link to TradingView and source/license links. The original full Apache
  2.0 LICENSE and NOTICE are preserved as UTF-8 files at
  fullstack/frontend/licenses/ and served as local text assets. Existing
  `layout.attributionLogo:true` remains enabled in the chart renderer.
- Using the library does **not** convey permission to republish NSE/Yahoo
  market data or confer any TradingView endorsement.
- The CDN is `unpkg.com` with an unpinned package version in this
  release. Pin the tested library version and review dependency updates as
  part of a separate technical hardening step; this attribution patch
  does not change the vendor JavaScript version.

Exact upstream NOTICE:

    TradingView Lightweight Charts™
    Copyright (с) 2025 TradingView, Inc. https://www.tradingview.com/

## Google News RSS — public republishing paused

The original public backend called
`https://news.google.com/rss/search` and returned Google-supplied
article titles and source-linked items with algorithmic sector hypotheses.
We have not established permission from Google and original publishers for
this specific public use. Linking to a publisher is not itself a sublicence.

Default public state:
- GET /api/news returns `feed_paused:true`, `items:[]`, and
  a curated set of direct links to official NSE, SEBI and RBI news pages.
- Public News Intelligence shows those external links instead of
  reproducing RSS headlines.
- The original parser and headline-mapping research code remain in the
  repository but are not called by default.
- Both private configuration flags are required before reuse:
  `IML_PUBLIC_NEWS_FEED_ENABLED=true` AND
  `IML_NEWS_REDISPLAY_RIGHTS_VERIFIED=true`.
- **Do not enable these flags without a documented rights review**
  covering the data provider, original publishers, intended audience,
  future monetization, attribution and re-publication constraints.
  Merely setting flags is not proof of permission.

Useful terms for review:
- https://policies.google.com/terms
- https://www.google.com/intl/en_us/terms_google_news.html
  (older product-specific terms; check current applicability)

## Bull/bear icon provenance — NOT CLOSED

The repository contains:
- fullstack/frontend/icons/bull.svg
- fullstack/frontend/icons/bear.svg
- fullstack/frontend/icons/bull-bear.svg

The SVGs use custom path data, but there is no verified documented
artist/source, source image permission, third-party licence, assignment,
or independent-original-art record in the repository.

Do not claim copyright ownership or licensed use without evidence.
The operator should supply the source, original design file, licence
receipt, or permission to use those specific symbols. If provenance
cannot be established, replace them with newly commissioned or verified
appropriately licensed art before a wider commercial launch.

## Current status and remaining checks

- Public exchange-derived prices and public file uploads stay paused.
- Public news syndication stays paused.
- Synthetic educational tools continue working.
- TradingView attribution is added; vendor CDN version pinning and
  actual browser appearance require separate verification.
- Bull/bear icon rights remain uncertain.
- No permissions are inferred from the existence of public source URLs.
- Product-specific NSE/SEBI review and permission for market data remain
  required before restoring price-driven features or paid services.

## Tests

`python -m pytest -q fullstack/backend/tests/test_legal.py`

Manual:
1. Open /third-party-licenses and verify the two-line TradingView notice.
2. Open /terminal and verify the footer notice and external TradingView link.
3. Open /#/news and verify links only, no copied current headlines.
4. GET /api/news returns paused=true and items=[].
