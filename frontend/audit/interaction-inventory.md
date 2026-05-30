# InfluenceIQ Phase 1 Interaction Inventory

Source root: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ`

This inventory lists the current vanilla JavaScript and inline event behavior that must be migrated to React client components.

## Shared Interactions From `_iiq-flow.js`

| Source | Behavior | Next.js Target |
|---|---|---|
| `_iiq-flow.js`, `window.iiqToast` | Creates fixed top-right toast root, animates toast in/out, supports success/info icon variants, default duration 3200ms | `src/components/ui/ToastProvider.tsx` |
| `_iiq-flow.js`, `window.iiqAttachNotif` | Appends notification dropdown to notification button, toggles open/closed, links ready shortlist notification to `Shortlist.html` | `src/components/ui/NotificationMenu.tsx` |
| `_iiq-flow.js`, `window.iiqAttachMe` | Appends account dropdown to account pill, toggles open/closed, links to settings/profile/logout | `src/components/ui/AccountMenu.tsx` |
| `_iiq-flow.js`, `window.iiqSavePopover` | Appends save-to-list popover, supports list checkboxes, create list input, cancel, save, and toast | `src/components/ui/SaveToListPopover.tsx` |
| `_iiq-flow.js`, DOMContentLoaded welcome toast | Shows welcome toast when `?welcome=1` exists | Dashboard client interaction using `useSearchParams` |

## Page Interactions

| Source Page | Current Behavior | Next.js Target |
|---|---|---|
| `InfluenceIQ.html` | Hero typewriter for `#typed` | `LandingInteractions.tsx` |
| `InfluenceIQ.html` | Logo marquee population in `#marquee-track` | `LandingInteractions.tsx` |
| `InfluenceIQ.html` | `.count-up` number animation | `LandingInteractions.tsx` |
| `InfluenceIQ.html` | Dashboard search Enter redirects to `Matching.html?next=Shortlist.html` if present | `router.push('/matching?next=/shortlist')` |
| `InfluenceIQ.html` | Showcase typewriter for `#sc-typed` | `LandingInteractions.tsx` |
| `InfluenceIQ.html` | `.sp-row` processing animation with timings `[550, 1200, 800, 600]` | `LandingInteractions.tsx` |
| `InfluenceIQ.html` | Pricing billing toggle updates `.price-value[data-price]` | `LandingInteractions.tsx` |
| `Signup.html` | Form submit prevents default and redirects to `Onboarding.html` | `/signup` client submit handler routes to `/onboarding` |
| `Onboarding.html` | `go(1/2/3)` switches `.step-view.active`, `.step-dot.on`, progress bars | `OnboardingStepper.tsx` |
| `Onboarding.html` | Goal card click toggles `.gcard.on` | `OnboardingStepper.tsx` |
| `Onboarding.html` | Platform card click toggles `.pcard.on` | `OnboardingStepper.tsx` |
| `Onboarding.html` | Budget range updates fill, thumb, and label | `OnboardingStepper.tsx` |
| `Onboarding.html` | Finish redirects to `Dashboard.html?welcome=1` | `router.push('/dashboard?welcome=1')` |
| `Dashboard.html` | `.count-up` number animation | `DashboardInteractions.tsx` |
| `Dashboard.html` | Recent search links normalized to `Shortlist.html` | Static route links to `/shortlist` |
| `Dashboard.html` | Top search Enter redirects to `Matching.html?next=Shortlist.html` | `router.push('/matching?next=/shortlist')` |
| `Discover.html` | Renders `const creators` into `#grid` using `innerHTML` | `DiscoverGrid.tsx` using typed data map |
| `Discover.html` | Budget and ER ranges update CSS custom property `--p` | `RangeFilter.tsx` |
| `Discover.html` | Natural language search button and Enter redirect to matching | `DiscoverSearch.tsx` |
| `Discover.html` | Suggestion chips fill natural language input | `DiscoverSearch.tsx` |
| `Discover.html` | Save buttons receive shared save popover | `SaveToListPopover.tsx` |
| `Discover.html` | Table view button redirects to `DiscoverTable.html` | Link or button to `/discover/table` |
| `DiscoverTable.html` | Renders table rows from `const data` | `DiscoverTable.tsx` |
| `DiscoverTable.html` | Row checkbox toggles `.row-cb.on` and `tr.selected` | React selection state |
| `DiscoverTable.html` | Header checkbox selects/clears all rendered rows | React selection state |
| `DiscoverTable.html` | Bulk bar visibility and selected count | React derived state |
| `DiscoverTable.html` | Clear selected button clears row state | React state update |
| `DiscoverTable.html` | Save selected shows toast or info message | `ToastProvider` |
| `DiscoverTable.html` | Sortable headers sort data by `th[data-k]` | React sort state |
| `DiscoverTable.html` | Quick search hides nonmatching rows | React filter state |
| `Lists.html` | Renders list cards from `const lists` | `ListsPageClient.tsx` |
| `Lists.html` | Renders detail table rows from `const detRows` | `ListsPageClient.tsx` |
| `Lists.html` | `openList(id)` toggles index/detail `.view.active` | React view state |
| `Lists.html` | `goIndex()` returns to list index | React view state |
| `Lists.html` | Detail row remove action removes row and shows toast | React state + `ToastProvider` |
| `Lists.html` | New list card uses `alert` | Preserve or replace with toast only if approved |
| `Brief.html` | Age/location chips toggle `.on` | `BriefForm.tsx` |
| `Brief.html` | Segment controls set one `.on` button | `BriefForm.tsx` |
| `Brief.html` | Tag input Enter creates removable chip | `BriefForm.tsx` |
| `Brief.html` | Budget range and min input update readout | `BriefForm.tsx` |
| `Brief.html` | Preview binds live form values using `data-bind` | `BriefForm.tsx` state-derived preview |
| `Brief.html` | Find matches shows loading overlay, animated steps, profile count, then redirects with query params | `BriefForm.tsx` |
| `Matching.html` | Particle generation | `MatchingAnimation.tsx` |
| `Matching.html` | Timed step animation with `[720, 600, 800, 700, 580]` | `MatchingAnimation.tsx` |
| `Matching.html` | Progress fill, percent, ticker updates | `MatchingAnimation.tsx` |
| `Matching.html` | Redirects to `next` query param or `Shortlist.html` | `/matching?next=/shortlist` |
| `Shortlist.html` | Parses brief data from query params | `briefQuery.ts` |
| `Shortlist.html` | Renders matches from `const matches` | `ShortlistPageClient.tsx` |
| `Shortlist.html` | Row selection toggles `.row.checked` and `.checkbox.on` | React selection state |
| `Shortlist.html` | Compare selected shows toast | `ToastProvider` |
| `Shortlist.html` | Export builds PDF preview sheet, opens overlay, locks body scroll | `ShortlistPageClient.tsx` |
| `Shortlist.html` | Preview close button, overlay click, Escape key close overlay | `ShortlistPageClient.tsx` |
| `Shortlist.html` | Print button calls `window.print()` | `ShortlistPageClient.tsx` |
| `Profile.html` | ROI budget input recalculates reach, engagement, CPE | `ProfileInteractions.tsx` |
| `Profile.html` | Save button receives shared save popover | `SaveToListPopover.tsx` |
| `Profile.html` | Contact modal open/close/overlay/cancel/submit | `ProfileInteractions.tsx` |
| `Profile.html` | Contact submit closes modal and shows success toast | `ToastProvider` |
| `Settings.html` | Notification switches toggle `.sw.on` via inline `onclick` | `SettingsToggles.tsx` |

## Data Arrays To Extract

| Source | Symbol | Next.js Data File |
|---|---|---|
| `Discover.html` | `creators` | `src/data/creators.ts` |
| `DiscoverTable.html` | `data` | `src/data/tableCreators.ts` |
| `Lists.html` | `lists` | `src/data/lists.ts` |
| `Lists.html` | `detRows` | `src/data/lists.ts` |
| `Shortlist.html` | `matches` | `src/data/matches.ts` |
| `_iiq-flow.js` | `LISTS` | `src/components/ui/SaveToListPopover.tsx` initial state |

## Migration Warnings

- Do not keep `_iiq-flow.js` as a global script in Next.js. It mutates the DOM and will fight React hydration.
- Do not change `alert` behavior in `Lists.html` unless the product owner approves the UX difference.
- Preserve animation timings exactly before cleanup.
- Preserve query parameter keys exactly.
- Preserve body scroll lock behavior for modals and previews.
