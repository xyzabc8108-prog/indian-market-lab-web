# Step 21.21.11 — Icon provenance and remediation

Date: 3 November 2026
Project: Indian Market Lab, GitHub xyzabc8108-prog/indian-market-lab-web

## 1. What was found

The former source files for the public bull, bear, and paired icons did not
include a verifiable creator name, purchase receipt, licence, source-asset
identification or documented permission. A previous CSS comment described
those silhouettes as traced from supplied artwork.

No conclusion is being drawn that those old images actually infringed
another party's rights; their permission status is simply unknown.

## 2. Remediation

The three active files have been completely replaced:

- fullstack/frontend/icons/bull.svg
- fullstack/frontend/icons/bear.svg
- fullstack/frontend/icons/bull-bear.svg

Replacement art was constructed specifically for this project in the
Step 21.21.11 source update from elementary SVG building blocks:
independently specified paths, ellipses, circles, filled shapes and strokes.

- The bull is a front-facing, green, angular head with simple curved horns,
  geometric ears, a chevron forehead and a rounded muzzle.
- The bear is a front-facing, red, rounded head with circular ears, downward
  chevron, eye dots and a simple nose.
- The paired icon places these newly constructed emblems side by side using
  embedded SVG viewports.

The old silhouettes' long SVG path definitions were **not imported, traced or
reused** to produce these replacements. No stock icon library, downloaded art,
external font, remote image or third-party animal SVG asset was used to
construct them.

All static references were updated with the version suffix
? v=iml-geom-20261103 (without the space) so browsers can refresh their
cached images. This update changes icon graphics; it does not change
market-data APIs, scanner rules, news rights or any trading settings.

## 3. Scope and remaining limitations

- This record documents how the new active source files were created.
- It is **not** a copyright registration, guarantee of legal ownership,
  trademark clearance, non-infringement search or legal opinion.
- The earlier designs may remain obtainable through previous Git commits,
  forks, screenshots or caches. Replacing HEAD assets does not erase history.
- Do not represent the former icons as your original creations.
- Preserve this file and the associated PR/change history as contemporaneous
  documentation. For commercial branding, consider independent design and
  trademark clearance by a qualified professional.
- If any credible third-party claim arises, review it promptly and consider
  temporarily replacing disputed icons with simple text labels while it is
  addressed.

## 4. Acceptance checklist

- GET /icons/bull.svg and /icons/bear.svg show new angular green and rounded
  red front-facing animal emblems with geometric shapes.
- GET /icons/bull-bear.svg shows the matching new paired version.
- New asset files have data-design=iml-original-geometry-2026-11-03.
- Old distinctive long SVG path data is absent from active icon files.
- A new version suffix appears on website icon URLs in the UI source.
- Terms, privacy, attribution, scanner and market-data restrictions remain
  intact and correctly configured.

Official background:
- https://ipindia.gov.in/pages/copyright/learn/basics-of-copyright
- https://www.wipo.int/en/web/copyright/protection
