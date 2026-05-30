# InfluenceIQ Phase 1 CSS And JavaScript Inventory

Source root: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ`

## CSS Token Contract

The core design tokens are defined in `:root` in `_iiq-shared.css` and repeated or extended inside large inline page styles.

Critical tokens to preserve:

```text
--ink
--ink-2
--ink-soft
--paper
--paper-2
--line
--line-soft
--muted
--muted-soft
--violet
--violet-soft
--violet-ink
--cyan
--cyan-soft
--cyan-ink
--coral
--coral-soft
--coral-ink
--good
--good-soft
--good-ink
--amber
--amber-soft
--amber-ink
--warn
--warn-soft
--warn-ink
--r
--r-lg
--r-xl
```

## Shared Shell Classes

These classes form the production shell and must be preserved exactly in the first migration pass:

```text
.app
.sidebar
.brand
.brand-mark
.nav-section-label
.side-link
.side-link.active
.side-link .ico
.side-link .count
.side-spacer
.upgrade-card
.main
.topbar
.crumbs
.topbar .right
.icon-btn
.me
.btn
.btn-primary
.btn-ghost
.btn-sm
.btn-lg
.i
.content
```

## Important Layout Constraints Found In Baseline Screenshots

- Workspace routes preserve a `252px` sidebar and content area grid.
- Several workspace pages keep a minimum horizontal content width on mobile. The captured mobile full-page screenshots show page widths greater than the viewport for routes such as dashboard, brief, shortlist, profile, and settings.
- This means the Next.js migration must not invent a collapsed mobile sidebar unless the product owner requests a redesign.
- Sticky elements include `.sidebar`, `.topbar`, `.preview`, `.brief-side`, table headers, and settings sub-nav.

## Page CSS Extraction Targets

| Source Page | CSS Source | Next.js CSS Target |
|---|---|---|
| `_iiq-shared.css` | Full file | `src/app/globals.css` |
| `InfluenceIQ.html` | inline style lines 10-2054 | `src/app/landing.css` |
| `Signup.html` | inline style lines 7-53 | `src/app/signup.css` |
| `Onboarding.html` | inline style lines 7-83 | `src/app/onboarding.css` |
| `Dashboard.html` | inline style lines 10-507 | `src/app/dashboard.css` |
| `Discover.html` | inline style lines 10-890 | `src/app/discover.css` |
| `DiscoverTable.html` | inline style lines 11-140 | `src/app/discover-table.css` |
| `Lists.html` | inline style lines 11-138 | `src/app/lists.css` |
| `Briefs.html` | inline style lines 7-62 | `src/app/briefs.css` |
| `Brief.html` | inline style lines 11-166 | `src/app/brief-new.css` |
| `Matching.html` | inline style lines 6-66 | `src/app/matching.css` |
| `Shortlist.html` | inline style lines 11-141 | `src/app/shortlist.css` |
| `Profile.html` | inline style lines 10-257 and line 750 keyframes | `src/app/profile.css` |
| `Settings.html` | inline style lines 7-65 | `src/app/settings.css` |

## JavaScript Extraction Targets

| Source | JS Start | JS End | Purpose | Next.js Target |
|---|---:|---:|---|---|
| `InfluenceIQ.html` | 2682 | 2814 | Landing animation and pricing behavior | `LandingInteractions.tsx` |
| `Signup.html` | inline form handler | inline form handler | Signup redirect | `/signup/page.tsx` client handler |
| `Onboarding.html` | 172 | 199 | Onboarding stepper and budget behavior | `OnboardingStepper.tsx` |
| `Dashboard.html` | 740 | 776 | Count-up and search redirect | `DashboardInteractions.tsx` |
| `Discover.html` | 1164 | 1291 | Creator grid, filters, search, save popovers | `DiscoverGrid.tsx`, `DiscoverSearch.tsx`, `RangeFilter.tsx` |
| `DiscoverTable.html` | 262 | 425 | Table render, selection, sorting, quick search | `DiscoverTable.tsx` |
| `Lists.html` | 236 | 376 | Saved list index/detail behavior | `ListsPageClient.tsx` |
| `Brief.html` | 507 | 633 | Brief form state, preview, loading redirect | `BriefForm.tsx` |
| `Matching.html` | 98 | 145 | Matching animation and redirect | `MatchingAnimation.tsx` |
| `Shortlist.html` | 264 | 476 | Query parsing, result render, select/export preview | `ShortlistPageClient.tsx` |
| `Profile.html` | 643 | 769 | ROI calculator and contact modal | `ProfileInteractions.tsx` |
| `Settings.html` | inline toggle handlers | inline toggle handlers | Toggle switches | `SettingsToggles.tsx` |
| `_iiq-flow.js` | 1 | 127 | Shared dropdowns/popovers/toasts | React UI components |

## CSS Migration Rules

- Copy first, refactor later.
- Keep page-specific CSS globally imported by each route during parity migration.
- Preserve cascade order: global shared shell CSS first, page CSS second.
- Replace only asset URLs needed for Next.js public paths.
- Do not rename class selectors during initial migration.
- Do not deduplicate repeated sidebar/topbar CSS until visual parity is approved.

## JavaScript Migration Rules

- Replace direct DOM mutation with React state.
- Replace `innerHTML` rendering with JSX maps.
- Replace `document.querySelectorAll(...).forEach(...)` class toggling with derived `className`.
- Replace `location.href` with `router.push`.
- Replace global functions on `window` with component props/hooks.
- Keep timing constants unchanged.
