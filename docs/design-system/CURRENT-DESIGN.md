# GrowthPilot — Current Design Implementation

> How the landing page and audit report actually look today.

---

## Design System: Azure Meridian

Based on "The Precision Architect" spec in `azure_meridian/DESIGN.md`. Key principles applied:

- **No borders for layout** — surface color shifts only
- **No divider lines** — spacing instead
- **No #000000 text** — always `on-surface` (#191c1e)
- **Mobile-first** — single column on phone, 2/3 + 1/3 on desktop

---

## Color Tokens (in use)

| Token | Value | Where used |
|---|---|---|
| `primary` | #0037b0 | CTA buttons, links, active states |
| `primary-container` | #1d4ed8 | Gradient end, score card |
| `surface` | #f7f9fb | Page background |
| `surface-container-low` | #f2f4f6 | Section backgrounds |
| `surface-container-lowest` | #ffffff | Cards |
| `surface-container-high` | #e6e8ea | Footer, muted elements |
| `on-surface` | #191c1e | Primary text |
| `on-surface-variant` | #434655 | Secondary text |
| `outline-variant` | #c4c5d7 | Ghost borders (15% opacity) |

### Status Colors

| Status | Background | Text |
|---|---|---|
| Green (good) | `bg-green-100` | `text-green-700` |
| Yellow (could be better) | `bg-amber-100` | `text-amber-700` |
| Red (needs attention) | `bg-red-100` | `text-red-700` |

---

## Typography

- **Headlines**: Manrope (extrabold, tight tracking)
- **Body**: Inter (regular, 400-600)
- **Size jumps**: Large gaps between headline and body for editorial tension

### Scale in use

| Element | Font | Weight | Size |
|---|---|---|---|
| Page title | Manrope | 800 | text-2xl / text-3xl |
| Section header | Manrope | 800 | text-base / text-lg |
| Card title | Manrope | 800 | text-sm |
| Body text | Inter | 400 | text-sm |
| Labels | Inter | 500-600 | text-xs |
| Muted text | Inter | 400 | text-xs |

---

## Icons

Material Symbols Outlined (variable font, weight 400, FILL 0).

Common icons in use:
- `restaurant` — business type indicator
- `location_on` — Google Maps
- `language` — website
- `public` — local presence
- `smart_toy` — AI readiness
- `restaurant_menu` — menu
- `check` / `close` — status indicators
- `arrow_forward` — pipeline connector
- `info` — tooltips
- `search` — search input
- `open_in_new` — external links

---

## Layout Patterns

### Landing Page

```
┌─────────────────────────────────────────────┐
│  Hero (gradient bg: primary → primary-container)  │
│  Search input + "Paste URL" fallback              │
├─────────────────────────────────────────────┤
│  How It Works (3 columns)                         │
├─────────────────────────────────────────────┤
│  Preview (mockup cards)                           │
├─────────────────────────────────────────────┤
│  Footer (surface-container-high bg)               │
└─────────────────────────────────────────────┘
```

### Audit Page

```
┌─────────────────────────────────────────────┐
│  Header (gradient bar, "GrowthPilot" centered)    │
├─────────────────────────────────────────────┤
│  🍴 Business Name                                 │
│     Address                                       │
│     ℹ Audited on date                             │
├─────────────────────────────────────────────┤
│  Pipeline Tracker (horizontal, full width)        │
│  ○ → ○ → ○ → ● → ○ → ○ → ○ → ○                 │
├──────────────────────┬──────────────────────┤
│  Results (2/3)       │  Soft Gate (1/3)     │
│                      │  sticky              │
│  1. GP Score         │                      │
│  2. Scorecard        │  "Get report on      │
│  3. How You Compare  │   WhatsApp"          │
│  4. Online Presence  │  [name]              │
│  5. Social Links     │  [email]             │
│  6. Delivery         │  [whatsapp]          │
│  7. Mentions         │  [Send]              │
│  8. Menu Highlights  │                      │
│  9. Price Position   │                      │
│ 10. Reviews          │                      │
│ 11. Opportunities    │                      │
├──────────────────────┴──────────────────────┤
│  Footer                                          │
└─────────────────────────────────────────────┘
```

Mobile: stacks vertically, soft gate below results.

---

## Component Patterns

### Cards

All content sections use the same card pattern:
```
rounded-lg bg-surface-container-lowest p-5 shadow-ambient
```
- White background
- 16px border radius
- 5 unit padding
- Ambient shadow (40px blur, 5% opacity, primary-tinted)

### Status Badges

```
rounded-full px-3 py-1 text-xs font-bold
```
Three states: green (Looking Good), yellow (Could Be Better), red (Needs Attention)

### Pipeline Tracker

Horizontal row of phase nodes connected by arrows:
- Pending: grey circle with dot
- Running: blue spinner
- Done: green circle with checkmark
- Rejected: amber circle with no-entry icon

Arrows turn green as phases complete.

### Tooltips

CSS-only hover tooltips using `group` / `group-hover`:
```
<div className="group relative">
  <Icon name="info" className="cursor-help" />
  <div className="hidden group-hover:block absolute ...">
    tooltip content
  </div>
</div>
```

### External Links

Clickable rows with favicon + title + domain + open-in-new icon:
```
<a href="..." target="_blank" className="flex items-start gap-3 rounded-lg p-3 hover:bg-surface-container-low">
  <img src={favicon} className="h-5 w-5 rounded" />
  <div>title + domain</div>
  <Icon name="open_in_new" />
</a>
```

---

## Signature Patterns

### Hero Gradient
```css
bg-gradient-to-br from-primary to-primary-container
```
Used for: landing hero, audit header, GrowthPilot Score card, soft gate CTA

### Glassmorphism
```css
bg-white/95 backdrop-blur-md shadow-ambient
```
Used for: search input on gradient background

### Tonal Layering
Depth via surface tier nesting:
- Page → `surface` (#f7f9fb)
- Section → `surface-container-low` (#f2f4f6)
- Card → `surface-container-lowest` (#ffffff)
- Footer → `surface-container-high` (#e6e8ea)

No drop shadows for depth — color shift only.

---

## Dual-Mode Search Input

Primary: autocomplete search with debounce
- Search icon prefix
- Dropdown: restaurant icon + name (highlighted match) + rating + reviews + address
- Max 5 results

Fallback: URL paste input
- Toggle link: "Can't find your restaurant? Paste Google Maps URL instead"
- Switch back: "Search by restaurant name instead"

---

## Audit Result Sections

### 1. GrowthPilot Score
- Gradient card (primary → primary-container)
- SVG circular progress ring (white on transparent)
- Score out of 5 with factor breakdown grid

### 2. Competitor Scorecard
- Table with horizontal scroll on mobile
- Columns: You + top 3 competitors
- Rows: Rating, Reviews, Website, Facebook, Instagram, TikTok, Foodpanda
- Green check / red X for boolean fields
- Info tooltip disclaimer

### 3. How You Compare
- 3-column grid: You vs Area Avg vs Top Competitor
- Reviews row + Rating row (separated by border)
- Color-coded: green with ↑ when ahead, red with ↓ when behind
- Info tooltip: "Real-time data from Google Maps"

### 4. Online Presence
- List of dimension rows: Google Maps, Menu, Website, Local Presence, AI Search Visibility
- Each row: icon + label + description + status badge
- Descriptions in plain language (not technical)

### 5. Social Links
- 4-column grid: Website, Facebook, Instagram, TikTok
- Green circle + check if found, red circle + X if not
- Shows handle (@username) or follower count if available

### 6. Delivery Platforms
- Found platforms: favicon + name + rating/reviews (from enrichment)
- Missing platforms: red X + "Not found — customers can't order from you here"

### 7. Where People Find You Online
- Top 3 external mentions (excluding own website)
- Favicon + title + domain + rating if available
- Opens in new tab

### 8. Menu Highlights (conditional)
- Grid of popular items from Google Maps
- Restaurant icon + item name + price
- Only shown if enrichment data exists

### 9. Price Positioning (conditional)
- Horizontal bar chart of spending distribution
- Percentage labels
- Only shown if price_details data exists

### 10. What Your Customers Say
- Summary paragraph
- Two columns: "Customers love" (green) / "Could improve" (red)
- Separate "Suggestions" section with amber lightbulb

### 11. Your Biggest Opportunities
- Severity-sorted gap list
- Icons: priority_high (red), warning (amber), info (blue)
- Plain language messages

---

## Soft Gate (CTA)

Right column, sticky on desktop. Gradient card.

Fields: Name (optional), Email (required), WhatsApp (required)
Button: "Send to WhatsApp"
Success: "We'll send this report on WhatsApp!"

---

## Responsive Behavior

| Breakpoint | Layout |
|---|---|
| Mobile (<1024px) | Single column, all sections stack |
| Desktop (lg+) | 2/3 results + 1/3 soft gate (sticky) |

Pipeline tracker scrolls horizontally on mobile.
Competitor scorecard table scrolls horizontally on mobile.
Social links grid: 2 columns on mobile, 4 on desktop.

---

## URLs

| Path | Page |
|---|---|
| `/` | Landing page |
| `/audit/{slug}` | Audit report (cached or new) |
| `/audit/{slug}?renew=true` | Force fresh audit |
| `/audit/_url` | Audit via pasted URL |
| Unknown path | 404 with header/footer |

---

---

## Design Tokens vs Reality

### In the `@growthpilot/ui` preset (`packages/ui/tailwind/preset.ts`)

```typescript
colors: {
  primary: "#0037b0",
  "primary-container": "#1d4ed8",
  surface: "#f7f9fb",
  "surface-container-low": "#f2f4f6",
  "surface-container-lowest": "#ffffff",
  "surface-container-high": "#e6e8ea",
  "on-surface": "#191c1e",
  "on-surface-variant": "#434655",
  "outline-variant": "#c4c5d7",
}
fontFamily: {
  headline: ["Manrope", "sans-serif"],
  body: ["Inter", "sans-serif"],
}
borderRadius: { md: "12px", lg: "16px", xl: "24px" }
boxShadow: { ambient: "0 4px 40px rgba(0, 55, 176, 0.05)" }
```

### NOT in the preset but used in code (from Tailwind defaults)

| Usage | Classes | Should formalize? |
|---|---|---|
| **Status: green** | `bg-green-100`, `text-green-600`, `text-green-700`, `bg-green-400` | Yes — define as `status-positive` |
| **Status: red** | `bg-red-100`, `text-red-500`, `text-red-700`, `bg-red-400` | Yes — define as `status-negative` |
| **Status: amber** | `bg-amber-100`, `text-amber-500`, `text-amber-700`, `bg-amber-400` | Yes — define as `status-warning` |
| **Opacity modifiers** | `text-white/80`, `bg-white/95`, `bg-primary/10` | OK as-is (Tailwind native) |
| **Gradient** | `bg-gradient-to-br from-primary to-primary-container` | OK — uses our tokens |
| **Spinner** | `border-primary border-t-transparent animate-spin` | OK |

### Missing from preset (should add)

```typescript
// Status colors — used consistently across all sections
colors: {
  "status-positive": "#16a34a",      // green-600
  "status-positive-bg": "#dcfce7",   // green-100
  "status-negative": "#ef4444",      // red-500
  "status-negative-bg": "#fee2e2",   // red-100
  "status-warning": "#f59e0b",       // amber-500
  "status-warning-bg": "#fef3c7",    // amber-100
}
```

### Fonts loaded in `index.html`

```html
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@600;800&family=Inter:wght@400;500;600&display=swap" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap" />
```

---

*Last updated: April 4, 2026*
