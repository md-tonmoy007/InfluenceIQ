# Manual Visual QA Checklist

## Viewports to Test
- [ ] 1440px (Desktop Wide)
- [ ] 1280px (Desktop Standard)
- [ ] 1024px (Tablet Landscape)
- [ ] 768px (Tablet Portrait)
- [ ] 430px (Mobile Large - iPhone Pro Max)
- [ ] 390px (Mobile Standard - iPhone)

## Route Checklist

### Landing Page (`/`)
- [ ] Hero typewriter animation functions correctly.
- [ ] Brand marquee track scrolls smoothly.
- [ ] Stat count-up animations trigger on view.
- [ ] Pricing toggle switches between Monthly/Yearly.
- [ ] "Get Started" buttons link to `/signup`.

### Workspace Shell
- [ ] Sidebar links point to correct Next.js routes.
- [ ] Active state in sidebar matches current route.
- [ ] Topbar breadcrumbs render correctly and link back.
- [ ] Notification menu opens/closes.
- [ ] Account menu opens/closes.

### Dashboard (`/dashboard`)
- [ ] Welcome toast appears (if `?welcome=1`).
- [ ] Stat cards render correctly with count-up animations.
- [ ] Search bar triggers `/matching?next=/shortlist` on Enter.
- [ ] Recent searches table links to `/shortlist`.

### Discover (`/discover` & `/discover/table`)
- [ ] View toggle switches between Grid and Table views.
- [ ] Search bar suggestions update input.
- [ ] Range filters (Budget/Engagement) update CSS variables.
- [ ] "Save to List" popover opens and functions.
- [ ] Table view: Row selection and bulk action bar.
- [ ] Table view: Column sorting.
- [ ] Table view: Quick search filter.

### Briefs (`/briefs` & `/briefs/new`)
- [ ] Brief cards render correctly.
- [ ] New Brief Form: Chip toggles (Ages/Locations).
- [ ] New Brief Form: Segmented controls (Gender/Currency).
- [ ] New Brief Form: Tag input for category/platforms.
- [ ] New Brief Form: Live preview panel updates on input.
- [ ] New Brief Form: Submit triggers matching animation.

### Matching Interstitial (`/matching`)
- [ ] Particle animation renders.
- [ ] Loading steps and progress bar advance.
- [ ] Automatic redirect to next route.

### Shortlist (`/shortlist`)
- [ ] Search param parsing (default values vs URL params).
- [ ] Row selection updates count.
- [ ] PDF Export modal opens and renders correctly.
- [ ] Print trigger calls `window.print()`.

### Saved Lists (`/lists`)
- [ ] Index/Detail view switching.
- [ ] Delete list confirmation and toast.
- [ ] Editable list name in detail view.
- [ ] Creator removal toast.

### Creator Profile (`/profile/[id]`)
- [ ] ROI Estimator recalculates on budget change.
- [ ] Contact modal opens/closes and handles submission.
- [ ] "Save to List" popover functions.

### Settings (`/settings`)
- [ ] Sub-navigation smooth scrolls and tracks active section.
- [ ] Notification toggles function correctly.
- [ ] Form fields render with default prototype values.
