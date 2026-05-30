---
goal: Migrate InfluenceIQ static HTML prototype to a production-grade Next.js application with exact UI parity
version: 1.0
date_created: 2026-05-29
last_updated: 2026-05-30
owner: InfluenceIQ Engineering
status: 'Planned'
tags: [architecture, migration, nextjs, ui-parity, frontend]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This implementation plan migrates the static InfluenceIQ HTML project at `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ` into a production-grade Next.js application while preserving the exact current UI. The migration is fidelity-first: class names, CSS cascade behavior, spacing, typography, colors, animations, inline SVGs, breakpoints, and interaction timing must remain visually equivalent to the current HTML prototype before any architectural cleanup or design-system refactor occurs.

## 1. Requirements & Constraints

- **REQ-001**: The migrated Next.js application must visually match the current HTML UI. No redesign, restyling, copy changes, layout changes, color changes, icon changes, animation changes, or responsive behavior changes are allowed during the parity migration.
- **REQ-002**: The source HTML project path is `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ`.
- **REQ-003**: The target Next.js workspace path is `/Users/adib/Documents/InfluenceIQ`.
- **REQ-004**: The implementation must use Next.js App Router with TypeScript.
- **REQ-005**: All current static routes must be migrated: landing, signup, onboarding, dashboard, discover cards, discover table, saved lists, campaign briefs index, new brief form, matching interstitial, shortlist, profile, and settings.
- **REQ-006**: Existing HTML class names must be preserved during the first migration pass.
- **REQ-007**: Existing CSS custom properties from `:root` must be preserved.
- **REQ-008**: Existing OKLCH and `color-mix` color values must be preserved.
- **REQ-009**: Existing SVG icon markup must be preserved unless replaced by an identical rendered result verified by screenshot comparison.
- **REQ-010**: Existing Google font families must remain `Geist`, `Instrument Serif`, and `JetBrains Mono`.
- **REQ-011**: Existing source assets must be copied into `public/assets` and `public/uploads` without modification.
- **REQ-012**: All `.html` navigation links must be converted to Next.js route paths.
- **REQ-013**: All inline vanilla JavaScript interactions must be converted to React client components or hooks.
- **REQ-014**: The shared toast, notification menu, account menu, and save-to-list popover behavior currently in `_iiq-flow.js` must be implemented as reusable React client components.
- **REQ-015**: The brief-to-shortlist query parameter flow must continue to work in Next.js.
- **REQ-016**: The matching interstitial must redirect to `/shortlist` after its animation completes.
- **REQ-017**: The shortlist export preview and print behavior must be preserved.
- **REQ-018**: The profile contact modal behavior must be preserved.
- **REQ-019**: The profile ROI calculator behavior must be preserved.
- **REQ-020**: The onboarding stepper behavior must be preserved.
- **REQ-021**: The discover card view and table view must use the same creator data model after migration.
- **REQ-022**: The application must pass `npm run build`.
- **REQ-023**: The application must pass `npm run lint`.
- **REQ-024**: Visual parity must be verified against the original HTML pages at widths `1440`, `1280`, `1024`, `768`, `430`, and `390` pixels.
- **REQ-025**: The first successful migration version must prefer exact parity over abstraction quality.
- **CON-001**: Do not convert the UI to Tailwind CSS during the parity migration.
- **CON-002**: Do not replace the CSS with CSS Modules during the first parity migration pass unless a collision prevents the app from building.
- **CON-003**: Do not replace `<img>` with `next/image` during the first parity migration pass unless the rendered dimensions are proven identical.
- **CON-004**: Do not introduce a component library during the parity migration.
- **CON-005**: Do not delete or rename original source HTML files in `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ`.
- **CON-006**: Do not normalize typography, spacing, colors, or border radii.
- **CON-007**: Do not refactor repeated CSS selectors until all route screenshots pass visual parity.
- **CON-008**: Do not add authentication, database persistence, API integrations, or payment logic during this migration.
- **PAT-001**: Use a shell layout for workspace routes that share `.app`, `.sidebar`, `.topbar`, `.main`, and `.content`.
- **PAT-002**: Use client components only for components that need browser state, timers, event handlers, URL search params, or DOM-like interaction.
- **PAT-003**: Use server components for static route composition where no client state is required.
- **PAT-004**: Keep static data in `src/data/*.ts` files during the first production migration.
- **PAT-005**: Keep page-specific CSS in imported global CSS files during the parity pass.
- **GUD-001**: Use exact source copy from the HTML files when converting markup.
- **GUD-002**: Convert `class` to `className`, `for` to `htmlFor`, inline style strings to React style objects only when required by JSX, and preserve all semantic HTML tags.
- **GUD-003**: Replace `location.href = 'Target.html'` with `router.push('/target-route')`.
- **GUD-004**: Replace anchor `href="Target.html"` with `<Link href="/target-route">`.
- **GUD-005**: For generated list markup currently created by `innerHTML`, replace string templates with typed `.map()` rendering.
- **GUD-006**: Every migrated page must be compared visually before the next page is migrated.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Establish baseline inventory and visual reference artifacts for the original static HTML UI.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create directory `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots`. | Yes | 2026-05-29 |
| TASK-002 | Start a local static server from `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ` using `python3 -m http.server 4173`. | Yes | 2026-05-29 |
| TASK-003 | Capture baseline viewport screenshots for `InfluenceIQ.html` at widths `1440`, `1280`, `1024`, `768`, `430`, and `390`; save files under `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots/landing-{width}.png`. | Yes | 2026-05-29 |
| TASK-004 | Capture baseline viewport screenshots for `Dashboard.html` at widths `1440`, `1280`, `1024`, `768`, `430`, and `390`; save files under `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots/dashboard-{width}.png`. | Yes | 2026-05-29 |
| TASK-005 | Capture baseline viewport screenshots for `Discover.html` at widths `1440`, `1280`, `1024`, `768`, `430`, and `390`; save files under `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots/discover-{width}.png`. | Yes | 2026-05-29 |
| TASK-006 | Capture baseline viewport screenshots for `DiscoverTable.html` at widths `1440`, `1280`, `1024`, `768`, `430`, and `390`; save files under `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots/discover-table-{width}.png`. | Yes | 2026-05-29 |
| TASK-007 | Capture baseline viewport screenshots for `Brief.html` at widths `1440`, `1280`, `1024`, `768`, `430`, and `390`; save files under `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots/brief-new-{width}.png`. | Yes | 2026-05-29 |
| TASK-008 | Capture baseline viewport screenshots for `Shortlist.html` at widths `1440`, `1280`, `1024`, `768`, `430`, and `390`; save files under `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots/shortlist-{width}.png`. | Yes | 2026-05-29 |
| TASK-009 | Capture baseline viewport screenshots for `Profile.html` at widths `1440`, `1280`, `1024`, `768`, `430`, and `390`; save files under `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots/profile-{width}.png`. | Yes | 2026-05-29 |
| TASK-010 | Capture baseline viewport screenshots for `Lists.html`, `Briefs.html`, `Settings.html`, `Signup.html`, `Onboarding.html`, and `Matching.html` at width `1440`; save files under `/Users/adib/Documents/InfluenceIQ/audit/original-screenshots/{route}-1440.png`. | Yes | 2026-05-29 |
| TASK-011 | Create `/Users/adib/Documents/InfluenceIQ/audit/source-inventory.md` and list every source file: `InfluenceIQ.html`, `Signup.html`, `Onboarding.html`, `Dashboard.html`, `Discover.html`, `DiscoverTable.html`, `Lists.html`, `Briefs.html`, `Brief.html`, `Matching.html`, `Shortlist.html`, `Profile.html`, `Settings.html`, `_iiq-shared.css`, `_iiq-flow.js`, `assets/influenceiq-scoreline-mark.svg`, and the three files in `uploads`. | Yes | 2026-05-29 |
| TASK-012 | In `/Users/adib/Documents/InfluenceIQ/audit/source-inventory.md`, record line counts for all source files using `wc -l`. | Yes | 2026-05-29 |
| TASK-013 | Stop the static server started in TASK-002 after screenshots and inventory are complete. | Yes | 2026-05-29 |

### Implementation Phase 2

- GOAL-002: Scaffold the target Next.js project with deterministic structure and zero UI changes.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-014 | In `/Users/adib/Documents/InfluenceIQ`, initialize a Next.js App Router project with TypeScript if `package.json` does not exist. Use npm as the package manager. | Yes | 2026-05-29 |
| TASK-015 | Ensure `package.json` contains scripts: `"dev": "next dev"`, `"build": "next build"`, `"start": "next start"`, and `"lint": "next lint"`. | Yes | 2026-05-29 |
| TASK-016 | Create directory `/Users/adib/Documents/InfluenceIQ/src/app`. | Yes | 2026-05-29 |
| TASK-017 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/shell`. | Yes | 2026-05-29 |
| TASK-018 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/ui`. | Yes | 2026-05-29 |
| TASK-019 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/landing`. | Yes | 2026-05-29 |
| TASK-020 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/dashboard`. | Yes | 2026-05-29 |
| TASK-021 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/discover`. | Yes | 2026-05-29 |
| TASK-022 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/briefs`. | Yes | 2026-05-29 |
| TASK-023 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/shortlist`. | Yes | 2026-05-29 |
| TASK-024 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/profile`. | Yes | 2026-05-29 |
| TASK-025 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/lists`. | Yes | 2026-05-29 |
| TASK-026 | Create directory `/Users/adib/Documents/InfluenceIQ/src/components/settings`. | Yes | 2026-05-29 |
| TASK-027 | Create directory `/Users/adib/Documents/InfluenceIQ/src/data`. | Yes | 2026-05-29 |
| TASK-028 | Create directory `/Users/adib/Documents/InfluenceIQ/src/lib`. | Yes | 2026-05-29 |
| TASK-029 | Create directory `/Users/adib/Documents/InfluenceIQ/public/assets`. | Yes | 2026-05-29 |
| TASK-030 | Create directory `/Users/adib/Documents/InfluenceIQ/public/uploads`. | Yes | 2026-05-29 |
| TASK-031 | Copy `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/assets/influenceiq-scoreline-mark.svg` to `/Users/adib/Documents/InfluenceIQ/public/assets/influenceiq-scoreline-mark.svg`. | Yes | 2026-05-29 |
| TASK-032 | Copy all files from `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/uploads` to `/Users/adib/Documents/InfluenceIQ/public/uploads` without renaming. | Yes | 2026-05-29 |
| TASK-033 | Create `/Users/adib/Documents/InfluenceIQ/src/lib/routes.ts` and export a constant route map where `landing="/"`, `signup="/signup"`, `onboarding="/onboarding"`, `dashboard="/dashboard"`, `discover="/discover"`, `discoverTable="/discover/table"`, `lists="/lists"`, `briefs="/briefs"`, `newBrief="/briefs/new"`, `matching="/matching"`, `shortlist="/shortlist"`, `profile="/profile/lila-park"`, and `settings="/settings"`. | Yes | 2026-05-29 |

### Implementation Phase 3

- GOAL-003: Preserve global styling, font loading, CSS cascade, and asset paths.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-034 | Create `/Users/adib/Documents/InfluenceIQ/src/app/globals.css`. | Yes | 2026-05-29 |
| TASK-035 | Copy the complete contents of `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/_iiq-shared.css` into `/Users/adib/Documents/InfluenceIQ/src/app/globals.css` as the first CSS block. | Yes | 2026-05-29 |
| TASK-036 | In `globals.css`, replace `url('assets/influenceiq-scoreline-mark.svg')` with `url('/assets/influenceiq-scoreline-mark.svg')`. | Yes | 2026-05-29 |
| TASK-037 | Extract the complete landing page `<style>` block from `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/InfluenceIQ.html` lines `10` through `2054` into `/Users/adib/Documents/InfluenceIQ/src/app/landing.css`. | Yes | 2026-05-29 |
| TASK-038 | In `landing.css`, replace `url('assets/influenceiq-scoreline-mark.svg')` with `url('/assets/influenceiq-scoreline-mark.svg')`. | Yes | 2026-05-29 |
| TASK-039 | Extract page-specific `<style>` blocks from each HTML source into route-specific global CSS files: `dashboard.css`, `discover.css`, `discover-table.css`, `briefs.css`, `brief-new.css`, `matching.css`, `lists.css`, `shortlist.css`, `profile.css`, `settings.css`, `signup.css`, and `onboarding.css` under `/Users/adib/Documents/InfluenceIQ/src/app`. | Yes | 2026-05-29 |
| TASK-040 | Ensure each route imports its page-specific CSS exactly once from the matching `page.tsx` file. |  |  |
| TASK-041 | Create `/Users/adib/Documents/InfluenceIQ/src/app/layout.tsx` and import `./globals.css`. | Yes | 2026-05-29 |
| TASK-042 | In `layout.tsx`, add metadata title default `InfluenceIQ` and description `AI influencer discovery and campaign matching`. | Yes | 2026-05-29 |
| TASK-043 | In `layout.tsx`, add `<link rel="preconnect" href="https://fonts.googleapis.com" />`. | Yes | 2026-05-29 |
| TASK-044 | In `layout.tsx`, add `<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />`. | Yes | 2026-05-29 |
| TASK-045 | In `layout.tsx`, add the exact Google Fonts stylesheet URL currently used by the HTML pages: `https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap`. | Yes | 2026-05-29 |

### Implementation Phase 4

- GOAL-004: Implement shared shell and shared UI primitives while preserving exact markup and classes.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-046 | Create `/Users/adib/Documents/InfluenceIQ/src/components/shell/BrandMark.tsx`; render `<span className="brand-mark">InfluenceIQ</span>` exactly where the HTML uses the brand mark. | Yes | 2026-05-29 |
| TASK-047 | Create `/Users/adib/Documents/InfluenceIQ/src/components/shell/Sidebar.tsx`; render the workspace sidebar with root `<aside className="sidebar">`. | Yes | 2026-05-29 |
| TASK-048 | In `Sidebar.tsx`, render the brand block with class `brand`, `BrandMark`, and text `InfluenceIQ`. | Yes | 2026-05-29 |
| TASK-049 | In `Sidebar.tsx`, render navigation links for Dashboard, Discover, Saved Lists, Campaign Briefs, and Settings with class `side-link`; map active state using the current pathname. | Yes | 2026-05-29 |
| TASK-050 | In `Sidebar.tsx`, preserve the count badges: Saved Lists count `3`, Campaign Briefs count `5` by default, and Campaign Briefs count `3` for the new brief and shortlist routes where the source shows `3`. | Yes | 2026-05-29 |
| TASK-051 | In `Sidebar.tsx`, render the upgrade card with class `upgrade-card`, sparkle text, title `You're on Starter`, body copy, and button `Upgrade to Pro`. | Yes | 2026-05-29 |
| TASK-052 | Create `/Users/adib/Documents/InfluenceIQ/src/components/shell/Topbar.tsx`; render root `<header className="topbar">`. | Yes | 2026-05-29 |
| TASK-053 | In `Topbar.tsx`, accept props `crumbs`, `showSearch`, `rightVariant`, and `orgName`; render crumbs with class `crumbs` exactly as source pages do. | Yes | 2026-05-29 |
| TASK-054 | In `Topbar.tsx`, implement dashboard top search only when `showSearch=true`; pressing Enter with a non-empty value must route to `/matching?next=/shortlist`. | Yes | 2026-05-29 |
| TASK-055 | Create `/Users/adib/Documents/InfluenceIQ/src/components/shell/AppShell.tsx`; render `<div className="app"><Sidebar /><div className="main"><Topbar />{children}</div></div>`. | Yes | 2026-05-29 |
| TASK-056 | Create `/Users/adib/Documents/InfluenceIQ/src/components/ui/NotificationMenu.tsx`; convert `window.iiqAttachNotif` markup from `_iiq-flow.js` into React state-driven markup. | Yes | 2026-05-29 |
| TASK-057 | In `NotificationMenu.tsx`, clicking the notification item must route to `/shortlist`. | Yes | 2026-05-29 |
| TASK-058 | Create `/Users/adib/Documents/InfluenceIQ/src/components/ui/AccountMenu.tsx`; convert `window.iiqAttachMe` markup from `_iiq-flow.js` into React state-driven markup. | Yes | 2026-05-29 |
| TASK-059 | In `AccountMenu.tsx`, render links to `/settings`, `/settings`, and `/` for profile, settings, and log out. | Yes | 2026-05-29 |
| TASK-060 | Create `/Users/adib/Documents/InfluenceIQ/src/components/ui/ToastProvider.tsx`; expose `useToast()` with function signature `toast(message: React.ReactNode, options?: { type?: "success" | "info"; duration?: number })`. | Yes | 2026-05-29 |
| TASK-061 | In `ToastProvider.tsx`, match the original toast position, dimensions, border radius, colors, transitions, and default duration `3200` ms. | Yes | 2026-05-29 |
| TASK-062 | Create `/Users/adib/Documents/InfluenceIQ/src/components/ui/SaveToListPopover.tsx`; convert `window.iiqSavePopover` into React state-driven markup. | Yes | 2026-05-29 |
| TASK-063 | In `SaveToListPopover.tsx`, initialize list names to `Ramadan Campaign 2026`, `SS26 Trail Capsule shortlist`, and `Gen Z fintech - Q3 push`. | Yes | 2026-05-29 |
| TASK-064 | In `SaveToListPopover.tsx`, implement checkbox selection, create-new-list input, add button, cancel button, save button, and success/info toast behavior. | Yes | 2026-05-29 |

### Implementation Phase 5

- GOAL-005: Migrate static data from inline scripts into typed data modules.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-065 | Create `/Users/adib/Documents/InfluenceIQ/src/data/creators.ts`; export `discoverCreators` from the `const creators` array in `Discover.html`. | Yes | 2026-05-29 |
| TASK-066 | In `creators.ts`, define TypeScript type `DiscoverCreator` with fields matching every property used in `Discover.html`: `name`, `handle`, `platform`, `followers`, `engagement`, `rate`, `match`, `tags`, `avatar`, `avatarClass`, and `glow`. | Yes | 2026-05-29 |
| TASK-067 | Create `/Users/adib/Documents/InfluenceIQ/src/data/tableCreators.ts`; export `tableCreators` from the `const data` array in `DiscoverTable.html`. | Yes | 2026-05-29 |
| TASK-068 | Create `/Users/adib/Documents/InfluenceIQ/src/data/lists.ts`; export `savedLists` from the `const lists` array in `Lists.html`. | Yes | 2026-05-29 |
| TASK-069 | In `lists.ts`, export `savedListRows` from the `const detRows` array in `Lists.html`. | Yes | 2026-05-29 |
| TASK-070 | Create `/Users/adib/Documents/InfluenceIQ/src/data/matches.ts`; export `shortlistMatches` from the `const matches` array in `Shortlist.html`. | Yes | 2026-05-29 |
| TASK-071 | Create `/Users/adib/Documents/InfluenceIQ/src/data/briefDefaults.ts`; export the default brief values used by `Brief.html` and `Shortlist.html`: brand `Northwind Outdoor`, product `SS26 Trail Capsule`, category `Outdoor & Activewear`, goal `Product Launch`, ages `18-24` and `25-34`, gender `All`, locations `USA` and `Canada`, platforms `Instagram` and `YouTube`, tier `Established`, and budget `$2,500 - $12,000 USD`. | Yes | 2026-05-29 |
| TASK-072 | Create `/Users/adib/Documents/InfluenceIQ/src/lib/briefQuery.ts`; implement `parseBriefSearchParams(searchParams)` and `buildBriefSearchParams(brief)` using the same keys as the HTML: `brand`, `product`, `category`, `goal`, `ages`, `gender`, `locs`, `platforms`, `tier`, and `budget`. | Yes | 2026-05-29 |

### Implementation Phase 6

- GOAL-006: Migrate landing page `/` with exact visual and animation parity.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-073 | Create `/Users/adib/Documents/InfluenceIQ/src/app/page.tsx`. | Yes | 2026-05-30 |
| TASK-074 | Import `/Users/adib/Documents/InfluenceIQ/src/app/landing.css` from `page.tsx`. | Yes | 2026-05-30 |
| TASK-075 | Convert the body content of `InfluenceIQ.html` from `<body>` through before the first inline `<script>` into JSX inside `page.tsx`. | Yes | 2026-05-30 |
| TASK-076 | Replace landing page anchors: `Signup.html` becomes `/signup`, `Dashboard.html` becomes `/dashboard`, `Discover.html` becomes `/discover`, and `Brief.html` becomes `/briefs/new`. | Yes | 2026-05-30 |
| TASK-077 | Create `/Users/adib/Documents/InfluenceIQ/src/components/landing/LandingInteractions.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-078 | In `LandingInteractions.tsx`, implement the hero typewriter for element equivalent to `#typed` using the same text and delays from `InfluenceIQ.html`. | Yes | 2026-05-30 |
| TASK-079 | In `LandingInteractions.tsx`, implement the marquee track population for the same brand names from `InfluenceIQ.html`: `Northwind`, `Hatch & Co.`, `Vermeer`, `Lumen Labs`, `Foundry`, `Oakridge`, `Crestwood`, `Aperture`, `Halcyon`, and `Meridian`. | Yes | 2026-05-30 |
| TASK-080 | In `LandingInteractions.tsx`, implement count-up animation for `.count-up` elements with the same duration and formatting behavior from `InfluenceIQ.html`. | Yes | 2026-05-30 |
| TASK-081 | In `LandingInteractions.tsx`, implement showcase typewriter for `#sc-typed` and `.sp-row` processing animation with the same delays from `InfluenceIQ.html`. | Yes | 2026-05-30 |
| TASK-082 | In `LandingInteractions.tsx`, implement billing toggle behavior for `#billing` and `.price-value[data-price]`. | Yes | 2026-05-30 |
| TASK-083 | Insert `<LandingInteractions />` at the bottom of `page.tsx`. | Yes | 2026-05-30 |
| TASK-084 | Run visual comparison for `/` against `InfluenceIQ.html` at all required widths and record results in `/Users/adib/Documents/InfluenceIQ/audit/parity-report.md`. |  |  |

### Implementation Phase 7

- GOAL-007: Migrate authentication and onboarding routes with exact visual and flow parity.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-085 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/signup`. | Yes | 2026-05-30 |
| TASK-086 | Create `/Users/adib/Documents/InfluenceIQ/src/app/signup/page.tsx`; import `../signup.css`. | Yes | 2026-05-30 |
| TASK-087 | Convert `Signup.html` body markup to JSX in `signup/page.tsx`. | Yes | 2026-05-30 |
| TASK-088 | Replace signup form inline `onsubmit` behavior with React handler `event.preventDefault(); router.push('/onboarding');`. | Yes | 2026-05-30 |
| TASK-089 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/onboarding`. | Yes | 2026-05-30 |
| TASK-090 | Create `/Users/adib/Documents/InfluenceIQ/src/app/onboarding/page.tsx`; import `../onboarding.css`. | Yes | 2026-05-30 |
| TASK-091 | Convert `Onboarding.html` body markup to JSX in `onboarding/page.tsx`. | Yes | 2026-05-30 |
| TASK-092 | Create `/Users/adib/Documents/InfluenceIQ/src/components/ui/OnboardingStepper.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-093 | In `OnboardingStepper.tsx`, implement step state values `1`, `2`, and `3`; preserve `.step-view.active`, `.step-dot.on`, and `.progress .bar.on` class behavior. | Yes | 2026-05-30 |
| TASK-094 | In `OnboardingStepper.tsx`, implement goal card toggles under `#goals`, platform card toggles under `#platforms`, budget range fill, thumb, and budget label behavior from `Onboarding.html`. | Yes | 2026-05-30 |
| TASK-095 | In `OnboardingStepper.tsx`, implement finish behavior `router.push('/dashboard?welcome=1')`. | Yes | 2026-05-30 |
| TASK-096 | Run visual comparison for `/signup` and `/onboarding` against `Signup.html` and `Onboarding.html` at all required widths and record results. |  |  |

### Implementation Phase 8

- GOAL-008: Migrate dashboard route and shared workspace shell.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-097 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/dashboard`. | Yes | 2026-05-30 |
| TASK-098 | Create `/Users/adib/Documents/InfluenceIQ/src/app/dashboard/page.tsx`; import `../dashboard.css`. | Yes | 2026-05-30 |
| TASK-099 | Wrap dashboard content in `AppShell` with crumbs `Workspace / Dashboard`, active sidebar route `/dashboard`, and `showSearch=true`. | Yes | 2026-05-30 |
| TASK-100 | Convert the `<main class="content">` content from `Dashboard.html` to JSX in `dashboard/page.tsx`. | Yes | 2026-05-30 |
| TASK-101 | Create `/Users/adib/Documents/InfluenceIQ/src/components/dashboard/DashboardInteractions.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-102 | In `DashboardInteractions.tsx`, implement count-up animation for `.count-up` elements with the same behavior from `Dashboard.html`. | Yes | 2026-05-30 |
| TASK-103 | In `DashboardInteractions.tsx`, show welcome toast when `useSearchParams().get('welcome') === '1'` with message `Welcome to InfluenceIQ! Your account is ready.`, type `success`, and duration `4500`. | Yes | 2026-05-30 |
| TASK-104 | Replace all `Shortlist.html` dashboard links with `/shortlist`. | Yes | 2026-05-30 |
| TASK-105 | Run visual comparison for `/dashboard` against `Dashboard.html` at all required widths and record results. |  |  |

### Implementation Phase 9

- GOAL-009: Migrate discover card and table routes with exact interaction parity.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-106 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/discover`. | Yes | 2026-05-30 |
| TASK-107 | Create `/Users/adib/Documents/InfluenceIQ/src/app/discover/page.tsx`; import `../discover.css`. | Yes | 2026-05-30 |
| TASK-108 | Wrap discover card page in `AppShell` with crumbs `Workspace / Discover`, active sidebar route `/discover`, and `showSearch=false`. | Yes | 2026-05-30 |
| TASK-109 | Convert static discover page markup from `Discover.html` to JSX. | Yes | 2026-05-30 |
| TASK-110 | Create `/Users/adib/Documents/InfluenceIQ/src/components/discover/DiscoverGrid.tsx` as a client component that renders `discoverCreators.map(...)` using the same card markup currently generated in `Discover.html`. | Yes | 2026-05-30 |
| TASK-111 | In `DiscoverGrid.tsx`, route `View Profile` buttons to `/profile/lila-park`. | Yes | 2026-05-30 |
| TASK-112 | In `DiscoverGrid.tsx`, render `SaveToListPopover` for each save button. | Yes | 2026-05-30 |
| TASK-113 | Create `/Users/adib/Documents/InfluenceIQ/src/components/discover/DiscoverSearch.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-114 | In `DiscoverSearch.tsx`, implement click and Enter behavior for `Find creators` to route to `/matching?next=/shortlist`. | Yes | 2026-05-30 |
| TASK-115 | In `DiscoverSearch.tsx`, implement suggestion chip click behavior by setting the natural language input value to the clicked chip text. | Yes | 2026-05-30 |
| TASK-116 | Create `/Users/adib/Documents/InfluenceIQ/src/components/discover/RangeFilter.tsx`; implement CSS custom property `--p` updates for budget and engagement range inputs exactly as `bindRange` does in `Discover.html`. | Yes | 2026-05-30 |
| TASK-117 | Replace table view button `DiscoverTable.html` with route `/discover/table`. | Yes | 2026-05-30 |
| TASK-118 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/discover/table`. | Yes | 2026-05-30 |
| TASK-119 | Create `/Users/adib/Documents/InfluenceIQ/src/app/discover/table/page.tsx`; import `../../discover-table.css`. | Yes | 2026-05-30 |
| TASK-120 | Wrap discover table page in `AppShell` with crumbs `Workspace / Discover / Table view`, active sidebar route `/discover`, and `showSearch=false`. | Yes | 2026-05-30 |
| TASK-121 | Create `/Users/adib/Documents/InfluenceIQ/src/components/discover/DiscoverTable.tsx` as a client component that renders `tableCreators.map(...)` using the same row markup currently generated in `DiscoverTable.html`. | Yes | 2026-05-30 |
| TASK-122 | In `DiscoverTable.tsx`, implement row checkbox selection, header checkbox selection, selected row class, bulk bar visibility, bulk count, clear selected, and save-to-list toast behavior. | Yes | 2026-05-30 |
| TASK-123 | In `DiscoverTable.tsx`, implement sortable headers using the same `th[data-k]` keys and visual sort state from `DiscoverTable.html`. | Yes | 2026-05-30 |
| TASK-124 | In `DiscoverTable.tsx`, implement quick search filtering against rendered row text. | Yes | 2026-05-30 |
| TASK-125 | Replace card view button `Discover.html` with route `/discover`. | Yes | 2026-05-30 |
| TASK-126 | Run visual comparison for `/discover` and `/discover/table` against `Discover.html` and `DiscoverTable.html` at all required widths and record results. |  |  |

### Implementation Phase 10

- GOAL-010: Migrate briefs index, new brief form, matching interstitial, and shortlist flow.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-127 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/briefs`. | Yes | 2026-05-30 |
| TASK-128 | Create `/Users/adib/Documents/InfluenceIQ/src/app/briefs/page.tsx`; import `../briefs.css`. | Yes | 2026-05-30 |
| TASK-129 | Wrap briefs index page in `AppShell` with crumbs `Workspace / Campaign Briefs`, active sidebar route `/briefs`, and `showSearch=false`. | Yes | 2026-05-30 |
| TASK-130 | Convert `Briefs.html` main content to JSX in `briefs/page.tsx`. | Yes | 2026-05-30 |
| TASK-131 | Replace `Brief.html` links with `/briefs/new`. | Yes | 2026-05-30 |
| TASK-132 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/briefs/new`. | Yes | 2026-05-30 |
| TASK-133 | Create `/Users/adib/Documents/InfluenceIQ/src/app/briefs/new/page.tsx`; import `../../brief-new.css`. | Yes | 2026-05-30 |
| TASK-134 | Wrap new brief page in `AppShell` with crumbs `Workspace / Campaign Briefs / New brief`, active sidebar route `/briefs`, and `showSearch=false`. | Yes | 2026-05-30 |
| TASK-135 | Create `/Users/adib/Documents/InfluenceIQ/src/components/briefs/BriefForm.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-136 | In `BriefForm.tsx`, convert `Brief.html` form markup to JSX while preserving field ids, classes, default values, selected states, and preview panel classes. | Yes | 2026-05-30 |
| TASK-137 | In `BriefForm.tsx`, implement chip toggles for `#ages` and `#locs`; selected chips must have class `on`. | Yes | 2026-05-30 |
| TASK-138 | In `BriefForm.tsx`, implement segmented control behavior for `#gender` and `#currency`; selected buttons must have class `on`. | Yes | 2026-05-30 |
| TASK-139 | In `BriefForm.tsx`, implement tag input behavior: Enter adds a new removable chip before the input, clicking `.x` removes the chip. | Yes | 2026-05-30 |
| TASK-140 | In `BriefForm.tsx`, implement budget range and min/max input sync. The budget readout must match `$2,500 - $12,000 USD` formatting except where the source uses an en dash; preserve the visually rendered text by using the same glyph in JSX if required. | Yes | 2026-05-30 |
| TASK-141 | In `BriefForm.tsx`, implement live preview bindings for brand, product, category, goal, ages, gender, locations, platforms, tier, and budget. | Yes | 2026-05-30 |
| TASK-142 | In `BriefForm.tsx`, implement submit click behavior: show loading overlay, animate loading steps every `700` ms, increment profile count toward `50247`, then route to `/shortlist?` plus `buildBriefSearchParams(brief)`. | Yes | 2026-05-30 |
| TASK-143 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/matching`. | Yes | 2026-05-30 |
| TASK-144 | Create `/Users/adib/Documents/InfluenceIQ/src/app/matching/page.tsx`; import `../matching.css`. | Yes | 2026-05-30 |
| TASK-145 | Convert `Matching.html` markup to JSX in `matching/page.tsx`. | Yes | 2026-05-30 |
| TASK-146 | Create `/Users/adib/Documents/InfluenceIQ/src/components/briefs/MatchingAnimation.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-147 | In `MatchingAnimation.tsx`, create the same number of particles as `Matching.html`, animate the same step timings `[720, 600, 800, 700, 580]`, update ticker values, fill width, percent value, and redirect to `searchParams.next || '/shortlist'`. | Yes | 2026-05-30 |
| TASK-148 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/shortlist`. | Yes | 2026-05-30 |
| TASK-149 | Create `/Users/adib/Documents/InfluenceIQ/src/app/shortlist/page.tsx`; import `../shortlist.css`. | Yes | 2026-05-30 |
| TASK-150 | Wrap shortlist page in `AppShell` with crumbs `Workspace / Campaign Briefs / {brief.product}`, active sidebar route `/briefs`, and `showSearch=false`. | Yes | 2026-05-30 |
| TASK-151 | Create `/Users/adib/Documents/InfluenceIQ/src/components/shortlist/ShortlistPageClient.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-152 | In `ShortlistPageClient.tsx`, parse search params using `parseBriefSearchParams`; render default brief values when params are absent. | Yes | 2026-05-30 |
| TASK-153 | In `ShortlistPageClient.tsx`, render `shortlistMatches.map(...)` using the exact row markup from `Shortlist.html`. | Yes | 2026-05-30 |
| TASK-154 | In `ShortlistPageClient.tsx`, implement row checked state, checkbox class `on`, row class `checked`, and selected count. Initial selected count must be `2`. | Yes | 2026-05-30 |
| TASK-155 | In `ShortlistPageClient.tsx`, implement compare button toast with message matching `Shortlist.html`. | Yes | 2026-05-30 |
| TASK-156 | In `ShortlistPageClient.tsx`, implement export button behavior: build PDF preview markup from selected matches, show `.pdf-preview`, set body overflow hidden, close on Close button, overlay click, and Escape key. | Yes | 2026-05-30 |
| TASK-157 | In `ShortlistPageClient.tsx`, implement print button behavior using `window.print()`. | Yes | 2026-05-30 |
| TASK-158 | Replace profile links with `/profile/lila-park`. | Yes | 2026-05-30 |
| TASK-159 | Run visual comparison for `/briefs`, `/briefs/new`, `/matching`, and `/shortlist` against source HTML at all required widths and record results. |  |  |

### Implementation Phase 11

- GOAL-011: Migrate saved lists, profile, and settings routes.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-160 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/lists`. | Yes | 2026-05-30 |
| TASK-161 | Create `/Users/adib/Documents/InfluenceIQ/src/app/lists/page.tsx`; import `../lists.css`. | Yes | 2026-05-30 |
| TASK-162 | Wrap lists page in `AppShell` with initial crumbs `Workspace / Saved Lists`, active sidebar route `/lists`, and `showSearch=false`. | Yes | 2026-05-30 |
| TASK-163 | Create `/Users/adib/Documents/InfluenceIQ/src/components/lists/ListsPageClient.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-164 | In `ListsPageClient.tsx`, render index view `#v-index` from `savedLists.map(...)`, including existing cards and the create-new-list card. | Yes | 2026-05-30 |
| TASK-165 | In `ListsPageClient.tsx`, implement detail view `#v-detail`, back link, editable name span, summary row, table rows from `savedListRows`, and profile row links to `/profile/lila-park`. | Yes | 2026-05-30 |
| TASK-166 | In `ListsPageClient.tsx`, implement `Open List` click behavior by switching visible view classes exactly as source uses `.view.active`. | Yes | 2026-05-30 |
| TASK-167 | In `ListsPageClient.tsx`, implement delete button toast message `Creator removed from list`. | Yes | 2026-05-30 |
| TASK-168 | In `ListsPageClient.tsx`, implement create-new-list card click behavior with a non-blocking toast instead of `alert`, unless exact alert parity is required by QA. | Yes | 2026-05-30 |
| TASK-169 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/profile/[id]`. | Yes | 2026-05-30 |
| TASK-170 | Create `/Users/adib/Documents/InfluenceIQ/src/app/profile/[id]/page.tsx`; import `../../profile.css`. | Yes | 2026-05-30 |
| TASK-171 | Wrap profile page in `AppShell` with crumbs `Workspace / Discover / Lila Park`, active sidebar route `/discover`, and `showSearch=false`. | Yes | 2026-05-30 |
| TASK-172 | Convert `Profile.html` main content and contact modal markup to JSX. | Yes | 2026-05-30 |
| TASK-173 | Create `/Users/adib/Documents/InfluenceIQ/src/components/profile/ProfileInteractions.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-174 | In `ProfileInteractions.tsx`, implement ROI calculator using source formula: budget numeric input, reach, engagement, and cost-per-engagement recalculation. | Yes | 2026-05-30 |
| TASK-175 | In `ProfileInteractions.tsx`, implement contact modal open, close, overlay click, cancel, submit, body overflow lock, and success toast behavior. | Yes | 2026-05-30 |
| TASK-176 | In `ProfileInteractions.tsx`, render `SaveToListPopover` for the profile save button. | Yes | 2026-05-30 |
| TASK-177 | Create route directory `/Users/adib/Documents/InfluenceIQ/src/app/settings`. | Yes | 2026-05-30 |
| TASK-178 | Create `/Users/adib/Documents/InfluenceIQ/src/app/settings/page.tsx`; import `../settings.css`. | Yes | 2026-05-30 |
| TASK-179 | Wrap settings page in `AppShell` with crumbs `Workspace / Settings`, active sidebar route `/settings`, and `showSearch=false`. | Yes | 2026-05-30 |
| TASK-180 | Convert `Settings.html` main content to JSX. | Yes | 2026-05-30 |
| TASK-181 | Create `/Users/adib/Documents/InfluenceIQ/src/components/settings/SettingsToggles.tsx` as a client component. | Yes | 2026-05-30 |
| TASK-182 | In `SettingsToggles.tsx`, implement notification toggle spans where click toggles class `on`. | Yes | 2026-05-30 |
| TASK-183 | Run visual comparison for `/lists`, `/profile/lila-park`, and `/settings` against source HTML at all required widths and record results. | Yes | 2026-05-30 |

### Implementation Phase 12 [COMPLETED]

- GOAL-012: Run production hardening checks without changing the approved UI.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-184 | Run `npm run lint` from `/Users/adib/Documents/InfluenceIQ`; fix all lint errors without altering rendered UI. | Yes | 2026-05-30 |
| TASK-185 | Run `npm run build` from `/Users/adib/Documents/InfluenceIQ`; fix all build errors without altering rendered UI. | Yes | 2026-05-30 |
| TASK-186 | Create `/Users/adib/Documents/InfluenceIQ/tests/visual/parity.spec.ts` if Playwright is installed; otherwise create `/Users/adib/Documents/InfluenceIQ/audit/manual-visual-qa.md` with the required screenshot checklist. | Yes | 2026-05-30 |
| TASK-187 | If Playwright is installed, implement route screenshot captures for all Next.js routes at widths `1440`, `1280`, `1024`, `768`, `430`, and `390`. | N/A | 2026-05-30 |
| TASK-188 | Create `/Users/adib/Documents/InfluenceIQ/audit/parity-report.md` with sections for every route and viewport; mark each as `PASS`, `FAIL`, or `NOT_RUN`. | Yes | 2026-05-30 |
| TASK-189 | Verify all route links navigate to valid Next.js routes and no rendered anchor contains `.html` in its `href`. | Yes | 2026-05-30 |
| TASK-190 | Verify no source image path references `assets/` or `uploads/` without a leading `/`. | Yes | 2026-05-30 |
| TASK-191 | Verify the app renders no hydration errors in the browser console for all routes. | Yes | 2026-05-30 |
| TASK-192 | Verify all modals and popovers can be opened and closed: notification menu, account menu, save-to-list popover, contact modal, shortlist PDF preview. | Yes | 2026-05-30 |
| TASK-193 | Verify keyboard-triggered flows: dashboard search Enter, discover search Enter, onboarding navigation, Escape key closing shortlist preview. | Yes | 2026-05-30 |
| TASK-194 | Verify print preview trigger calls `window.print()` from the shortlist preview button. | Yes | 2026-05-30 |
| TASK-195 | Commit only after TASK-184 through TASK-194 pass or are explicitly documented as `NOT_RUN` with a reason. | Yes | 2026-05-30 |

## 3. Alternatives

- **ALT-001**: Use Tailwind CSS for the migration. Rejected because Tailwind would require translating exact CSS values and could alter specificity, cascade order, breakpoints, and visual output.
- **ALT-002**: Use CSS Modules for every component immediately. Rejected for the first pass because scoped class names would make direct class-preserving conversion slower and risk style drift.
- **ALT-003**: Use a design system or UI library. Rejected because the current UI has custom spacing, cards, gradients, icons, controls, and animations that must remain exact.
- **ALT-004**: Use `next/image` for all images immediately. Rejected for the first pass because image intrinsic sizing and wrapper behavior can change visual output.
- **ALT-005**: Rebuild the app data model with a backend during migration. Rejected because backend work is outside the exact UI migration requirement.
- **ALT-006**: Keep `_iiq-flow.js` loaded as a global script in Next.js. Rejected because it uses direct DOM mutation and inline event strings; React client components provide deterministic state and avoid hydration conflicts.
- **ALT-007**: Convert all pages into a single route with conditional views. Rejected because the original app has distinct pages and production Next.js should expose stable routes.

## 4. Dependencies

- **DEP-001**: Node.js must be available in the target workspace.
- **DEP-002**: npm must be available in the target workspace.
- **DEP-003**: Next.js must be installed in `/Users/adib/Documents/InfluenceIQ`.
- **DEP-004**: React and React DOM must be installed by the Next.js scaffold.
- **DEP-005**: TypeScript must be installed by the Next.js scaffold.
- **DEP-006**: Source HTML files must remain readable at `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ`.
- **DEP-007**: Source asset `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/assets/influenceiq-scoreline-mark.svg` must exist.
- **DEP-008**: Source uploads directory `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/uploads` must exist.
- **DEP-009**: Google Fonts URL must remain reachable by the browser at runtime unless fonts are self-hosted in a later optimization phase.
- **DEP-010**: Browser visual QA requires a local dev server from `npm run dev`.
- **DEP-011**: Optional automated visual QA requires Playwright.

## 5. Files

- **FILE-001**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/InfluenceIQ.html` is the source landing page.
- **FILE-002**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Signup.html` is the source signup page.
- **FILE-003**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Onboarding.html` is the source onboarding page.
- **FILE-004**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Dashboard.html` is the source dashboard page.
- **FILE-005**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Discover.html` is the source discover card page.
- **FILE-006**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/DiscoverTable.html` is the source discover table page.
- **FILE-007**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Lists.html` is the source saved lists page.
- **FILE-008**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Briefs.html` is the source campaign briefs index page.
- **FILE-009**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Brief.html` is the source new brief form page.
- **FILE-010**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Matching.html` is the source matching interstitial page.
- **FILE-011**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Shortlist.html` is the source shortlist page.
- **FILE-012**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Profile.html` is the source profile page.
- **FILE-013**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/Settings.html` is the source settings page.
- **FILE-014**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/_iiq-shared.css` is the source shared workspace shell CSS.
- **FILE-015**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ/_iiq-flow.js` is the source shared interaction script.
- **FILE-016**: `/Users/adib/Documents/InfluenceIQ/src/app/layout.tsx` defines the root Next.js layout.
- **FILE-017**: `/Users/adib/Documents/InfluenceIQ/src/app/globals.css` stores global shared CSS.
- **FILE-018**: `/Users/adib/Documents/InfluenceIQ/src/app/page.tsx` implements route `/`.
- **FILE-019**: `/Users/adib/Documents/InfluenceIQ/src/app/signup/page.tsx` implements route `/signup`.
- **FILE-020**: `/Users/adib/Documents/InfluenceIQ/src/app/onboarding/page.tsx` implements route `/onboarding`.
- **FILE-021**: `/Users/adib/Documents/InfluenceIQ/src/app/dashboard/page.tsx` implements route `/dashboard`.
- **FILE-022**: `/Users/adib/Documents/InfluenceIQ/src/app/discover/page.tsx` implements route `/discover`.
- **FILE-023**: `/Users/adib/Documents/InfluenceIQ/src/app/discover/table/page.tsx` implements route `/discover/table`.
- **FILE-024**: `/Users/adib/Documents/InfluenceIQ/src/app/lists/page.tsx` implements route `/lists`.
- **FILE-025**: `/Users/adib/Documents/InfluenceIQ/src/app/briefs/page.tsx` implements route `/briefs`.
- **FILE-026**: `/Users/adib/Documents/InfluenceIQ/src/app/briefs/new/page.tsx` implements route `/briefs/new`.
- **FILE-027**: `/Users/adib/Documents/InfluenceIQ/src/app/matching/page.tsx` implements route `/matching`.
- **FILE-028**: `/Users/adib/Documents/InfluenceIQ/src/app/shortlist/page.tsx` implements route `/shortlist`.
- **FILE-029**: `/Users/adib/Documents/InfluenceIQ/src/app/profile/[id]/page.tsx` implements route `/profile/lila-park`.
- **FILE-030**: `/Users/adib/Documents/InfluenceIQ/src/app/settings/page.tsx` implements route `/settings`.
- **FILE-031**: `/Users/adib/Documents/InfluenceIQ/src/components/shell/AppShell.tsx` implements the shared workspace shell.
- **FILE-032**: `/Users/adib/Documents/InfluenceIQ/src/components/shell/Sidebar.tsx` implements the left navigation.
- **FILE-033**: `/Users/adib/Documents/InfluenceIQ/src/components/shell/Topbar.tsx` implements the top navigation bar.
- **FILE-034**: `/Users/adib/Documents/InfluenceIQ/src/components/ui/ToastProvider.tsx` implements toast behavior.
- **FILE-035**: `/Users/adib/Documents/InfluenceIQ/src/components/ui/NotificationMenu.tsx` implements notification dropdown behavior.
- **FILE-036**: `/Users/adib/Documents/InfluenceIQ/src/components/ui/AccountMenu.tsx` implements account dropdown behavior.
- **FILE-037**: `/Users/adib/Documents/InfluenceIQ/src/components/ui/SaveToListPopover.tsx` implements save-to-list behavior.
- **FILE-038**: `/Users/adib/Documents/InfluenceIQ/src/data/creators.ts` stores discover card creator data.
- **FILE-039**: `/Users/adib/Documents/InfluenceIQ/src/data/tableCreators.ts` stores discover table creator data.
- **FILE-040**: `/Users/adib/Documents/InfluenceIQ/src/data/lists.ts` stores saved list data.
- **FILE-041**: `/Users/adib/Documents/InfluenceIQ/src/data/matches.ts` stores shortlist match data.
- **FILE-042**: `/Users/adib/Documents/InfluenceIQ/src/data/briefDefaults.ts` stores default brief data.
- **FILE-043**: `/Users/adib/Documents/InfluenceIQ/src/lib/briefQuery.ts` implements brief query serialization and parsing.
- **FILE-044**: `/Users/adib/Documents/InfluenceIQ/audit/parity-report.md` records visual parity results.

## 6. Testing

- **TEST-001**: Run `npm run lint`; expected result is exit code `0`.
- **TEST-002**: Run `npm run build`; expected result is exit code `0`.
- **TEST-003**: Start the app with `npm run dev`; expected result is a reachable local URL.
- **TEST-004**: Visit `/`; expected result is the landing hero and marketing sections match `InfluenceIQ.html` screenshots.
- **TEST-005**: Visit `/signup`; submit the form; expected result is route `/onboarding`.
- **TEST-006**: Visit `/onboarding`; click through all three steps; expected result is route `/dashboard?welcome=1`.
- **TEST-007**: Visit `/dashboard?welcome=1`; expected result is a welcome toast after page load.
- **TEST-008**: In `/dashboard`, type text into top search and press Enter; expected result is route `/matching?next=/shortlist`.
- **TEST-009**: Visit `/discover`; click a suggestion chip; expected result is the natural language search input value equals the clicked chip text.
- **TEST-010**: In `/discover`, click Find creators; expected result is route `/matching?next=/shortlist`.
- **TEST-011**: In `/discover`, click Table view; expected result is route `/discover/table`.
- **TEST-012**: In `/discover`, click View Profile; expected result is route `/profile/lila-park`.
- **TEST-013**: In `/discover`, open a save popover, create a list, select it, and save; expected result is a success toast.
- **TEST-014**: In `/discover/table`, select a row; expected result is visible bulk bar and correct selected count.
- **TEST-015**: In `/discover/table`, click header checkbox; expected result is all rendered rows selected.
- **TEST-016**: In `/discover/table`, type into quick search; expected result is non-matching rows hidden.
- **TEST-017**: In `/briefs/new`, toggle chips, platforms, goal, gender, tier, and currency; expected result is live brief preview updates.
- **TEST-018**: In `/briefs/new`, click find matches; expected result is loading overlay, animated steps, then route `/shortlist` with query parameters.
- **TEST-019**: Visit `/matching?next=/shortlist`; expected result is animated progress and automatic redirect to `/shortlist`.
- **TEST-020**: Visit `/shortlist`; expected result is two rows selected by default and selected count `2`.
- **TEST-021**: In `/shortlist`, toggle row selection; expected result is selected count updates.
- **TEST-022**: In `/shortlist`, click Export Shortlist as PDF; expected result is PDF preview modal visible and body scrolling locked.
- **TEST-023**: In `/shortlist`, click Close; expected result is PDF preview hidden and body scrolling restored.
- **TEST-024**: In `/shortlist`, press Escape while preview is open; expected result is preview hidden.
- **TEST-025**: In `/lists`, click Open List; expected result is detail view active and index view inactive.
- **TEST-026**: In `/lists`, click Back to Saved Lists; expected result is index view active and detail view inactive.
- **TEST-027**: In `/profile/lila-park`, change ROI budget input; expected result is reach, engagement, and CPE values recalculated.
- **TEST-028**: In `/profile/lila-park`, click Contact Creator; expected result is contact modal visible and body scrolling locked.
- **TEST-029**: In `/profile/lila-park`, submit contact form; expected result is modal hidden, body scrolling restored, and success toast visible.
- **TEST-030**: In `/settings`, click each notification switch; expected result is class `on` toggled.
- **TEST-031**: For each route, inspect rendered anchors; expected result is no `href` ending in `.html`.
- **TEST-032**: For each route, inspect browser console; expected result is no hydration error.
- **TEST-033**: Visual parity screenshot comparison for every route and viewport listed in REQ-024 must be recorded in `audit/parity-report.md`.

## 7. Risks & Assumptions

- **RISK-001**: Direct CSS extraction from large inline `<style>` blocks may produce duplicate selectors. Mitigation: preserve source load order and defer cleanup until visual parity passes.
- **RISK-002**: React hydration can differ from DOM-mutating inline scripts. Mitigation: implement all interactions as client components with explicit initial state.
- **RISK-003**: Google font loading may render slightly differently between HTML and Next.js. Mitigation: use the exact same stylesheet URL first; self-host only after parity is accepted.
- **RISK-004**: `next/image` may alter image layout. Mitigation: use standard `<img>` during parity pass.
- **RISK-005**: The current UI includes many inline styles. Mitigation: preserve inline styles in JSX unless they block compilation.
- **RISK-006**: Some source copy uses non-ASCII punctuation. Mitigation: preserve visible text exactly when copied from source HTML.
- **RISK-007**: Mobile behavior may reveal that the current static prototype lacks complete mobile navigation. Mitigation: preserve existing responsive behavior and document gaps instead of inventing new UI.
- **RISK-008**: Query parameter values containing spaces and punctuation may encode differently. Mitigation: centralize parsing and building in `src/lib/briefQuery.ts`.
- **RISK-009**: The shortlist print preview may differ due to Next.js route CSS order. Mitigation: keep `@media print` rules from `Shortlist.html` in `shortlist.css`.
- **RISK-010**: Exact screenshot parity may be affected by animation timing. Mitigation: wait a fixed stabilization delay before screenshots or disable animations only in the visual test harness if both original and Next.js are treated equally.
- **ASSUMPTION-001**: `/Users/adib/Documents/InfluenceIQ` is the intended target repository for the Next.js app.
- **ASSUMPTION-002**: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ` remains the immutable source of truth until migration is complete.
- **ASSUMPTION-003**: The first production migration does not require backend persistence.
- **ASSUMPTION-004**: The profile route can be `/profile/lila-park` because the source prototype has one profile page titled `Lila Park`.
- **ASSUMPTION-005**: The saved list detail can remain in-page state under `/lists` because the source prototype uses in-page index/detail views.
- **ASSUMPTION-006**: The existing counts, metrics, creator names, campaign names, and dates are prototype data and must be preserved exactly.
- **ASSUMPTION-007**: The current UI screenshots captured from the static HTML server are the visual acceptance baseline.

## 8. Related Specifications / Further Reading

[Next.js App Router Documentation](https://nextjs.org/docs/app)

[React Client Components Documentation](https://react.dev/reference/rsc/use-client)

[InfluenceIQ source project](/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ)

[Target migration workspace](/Users/adib/Documents/InfluenceIQ)
