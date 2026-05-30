# InfluenceIQ Phase 1 Source Inventory

Source root: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ`

Target audit root: `/Users/adib/Documents/InfluenceIQ/audit`

Inventory date: 2026-05-29

## Source Files

| File | Type | Lines | Bytes | Role |
|---|---:|---:|---:|---|
| `InfluenceIQ.html` | HTML | 2819 | 105738 | Landing page, marketing sections, pricing, landing animations |
| `Signup.html` | HTML | 100 | 9380 | Signup/auth entry page |
| `Onboarding.html` | HTML | 200 | 17642 | Three-step onboarding flow |
| `Dashboard.html` | HTML | 778 | 30548 | Workspace dashboard |
| `Discover.html` | HTML | 1293 | 54336 | Creator discovery card grid |
| `DiscoverTable.html` | HTML | 427 | 36013 | Creator discovery table view |
| `Lists.html` | HTML | 378 | 30102 | Saved lists index/detail view |
| `Briefs.html` | HTML | 181 | 16000 | Campaign briefs index |
| `Brief.html` | HTML | 635 | 43700 | New campaign brief form |
| `Matching.html` | HTML | 147 | 12001 | Matching/progress interstitial |
| `Shortlist.html` | HTML | 478 | 34562 | AI shortlist results and PDF preview |
| `Profile.html` | HTML | 772 | 54571 | Creator profile and outreach modal |
| `Settings.html` | HTML | 199 | 16050 | Account settings |
| `_iiq-shared.css` | CSS | 65 | 6217 | Shared workspace shell styles |
| `_iiq-flow.js` | JS | 127 | 12367 | Shared toast, notification, account, save-to-list interactions |
| `assets/influenceiq-scoreline-mark.svg` | SVG | n/a | n/a | Brand mark used by `.brand-mark` |
| `uploads/CleanShot 2026-05-19 at 01.11.11@2x.png` | PNG | n/a | n/a | Uploaded visual asset |
| `uploads/CleanShot 2026-05-19 at 01.11.37@2x.png` | PNG | n/a | n/a | Uploaded visual asset |
| `uploads/CleanShot 2026-05-19 at 01.12.06@2x.png` | PNG | n/a | n/a | Uploaded visual asset |

## Shared CSS Usage

These pages load `_iiq-shared.css`:

| Page | Shared CSS | Page Inline CSS |
|---|---|---|
| `Brief.html` | yes | lines 11-166 |
| `Briefs.html` | yes | lines 7-62 |
| `DiscoverTable.html` | yes | lines 11-140 |
| `Lists.html` | yes | lines 11-138 |
| `Settings.html` | yes | lines 7-65 |
| `Shortlist.html` | yes | lines 11-141 |
| `Signup.html` | yes | lines 7-53 |
| `Onboarding.html` | yes | lines 7-83 |

These pages define a mostly self-contained shell and styles inline:

| Page | Inline CSS |
|---|---|
| `InfluenceIQ.html` | lines 10-2054 |
| `Dashboard.html` | lines 10-507 |
| `Discover.html` | lines 10-890 |
| `Matching.html` | lines 6-66 |
| `Profile.html` | lines 10-257 plus `popIn` style at line 750 |

## External Font Contract

All pages use the same Google Fonts URL:

```text
https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap
```

The Next.js migration must keep these font families and weights visually identical before any font optimization.

## Asset Path Contract

The source CSS references:

```text
assets/influenceiq-scoreline-mark.svg
```

The Next.js migration should copy the source asset to:

```text
public/assets/influenceiq-scoreline-mark.svg
```

Then update CSS references to:

```text
/assets/influenceiq-scoreline-mark.svg
```

## Notes For Migration

- Preserve original class names during the first migration pass.
- Preserve inline SVG markup during the first migration pass.
- Preserve inline style values when converting to JSX unless they block compilation.
- Preserve page-specific CSS order after `_iiq-shared.css`.
- Do not introduce Tailwind, CSS Modules, a UI kit, or `next/image` until after visual parity is accepted.
