# InfluenceIQ Phase 1 Route Map

Source root: `/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ`

Recommended Next.js target root: `/Users/adib/Documents/InfluenceIQ`

## Static HTML To Next.js Route Mapping

| Source HTML | Current Title | Main H1 / View Signal | Next.js Route | Shell |
|---|---|---|---|---|
| `InfluenceIQ.html` | `InfluenceIQ — Find the Perfect Influencer. Instantly.` | `Find the perfect influencer. Instantly.` | `/` | Landing nav |
| `Signup.html` | `InfluenceIQ — Sign up` | `Start finding your perfect creators.` | `/signup` | Auth split layout |
| `Onboarding.html` | `InfluenceIQ — Welcome` | `Tell us about your brand.` | `/onboarding` | Onboarding top/progress |
| `Dashboard.html` | `InfluenceIQ — Dashboard` | `Good morning, Elena — let's launch.` | `/dashboard` | Workspace shell |
| `Discover.html` | `InfluenceIQ — Discover` | `Discover creators.` | `/discover` | Workspace shell |
| `DiscoverTable.html` | `InfluenceIQ — Discover (Table)` | `Discover creators.` | `/discover/table` | Workspace shell |
| `Lists.html` | `InfluenceIQ — Saved Lists` | `Saved lists.` and detail view `Ramadan Campaign 2026` | `/lists` | Workspace shell |
| `Briefs.html` | `InfluenceIQ — Campaign Briefs` | `Campaign briefs.` | `/briefs` | Workspace shell |
| `Brief.html` | `InfluenceIQ — New Campaign Brief` | `New campaign brief.` | `/briefs/new` | Workspace shell |
| `Matching.html` | `InfluenceIQ — Matching…` | `Finding your perfect creators…` | `/matching` | Full-screen interstitial |
| `Shortlist.html` | `InfluenceIQ — AI Shortlist` | `Top matches for Northwind Outdoor's campaign` | `/shortlist` | Workspace shell |
| `Profile.html` | `InfluenceIQ — Lila Park` | `Lila Park` | `/profile/lila-park` | Workspace shell |
| `Settings.html` | `InfluenceIQ — Settings` | `Account settings.` | `/settings` | Workspace shell |

## Navigation Rewrites

| Source Link / Redirect | Next.js Destination |
|---|---|
| `InfluenceIQ.html` | `/` |
| `Signup.html` | `/signup` |
| `Onboarding.html` | `/onboarding` |
| `Dashboard.html` | `/dashboard` |
| `Discover.html` | `/discover` |
| `DiscoverTable.html` | `/discover/table` |
| `Lists.html` | `/lists` |
| `Briefs.html` | `/briefs` |
| `Brief.html` | `/briefs/new` |
| `Matching.html?next=Shortlist.html` | `/matching?next=/shortlist` |
| `Shortlist.html` | `/shortlist` |
| `Shortlist.html?{brief query}` | `/shortlist?{brief query}` |
| `Profile.html` | `/profile/lila-park` |
| `Settings.html` | `/settings` |

## Shared Workspace Shell Routes

These routes should use a shared `AppShell` component:

```text
/dashboard
/discover
/discover/table
/lists
/briefs
/briefs/new
/shortlist
/profile/lila-park
/settings
```

`AppShell` must preserve:

- root `.app`
- left `.sidebar`
- `.brand` and `.brand-mark`
- `.nav-section-label`
- `.side-link`
- `.upgrade-card`
- right `.main`
- sticky `.topbar`
- `.crumbs`
- `.content`

## Non-Workspace Routes

These routes should not use the workspace shell:

```text
/
/signup
/onboarding
/matching
```

## Query Parameter Contract

`Brief.html` builds query parameters for `Shortlist.html`.

Keys to preserve exactly:

```text
brand
product
category
goal
ages
gender
locs
platforms
tier
budget
```

`Shortlist.html` parses the same keys and falls back to default brief values when missing.
