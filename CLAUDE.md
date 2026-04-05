# GrowthPilot

We make local businesses easier to find online — starting with Dhaka restaurants.

Product document: `docs/idea/growthpilot-product-document.md`

## Project Status

MVP-0 engine complete (audit pipeline, mission generation, content drafts, multi-location, 84 tests). Now pivoting to **MVP-1: The Hook Works** — free audit funnel targeting Dhaka restaurant owners.

### Target Market

- **Who**: Restaurant/café owners in Dhaka, Bangladesh
- **Starting area**: Mirpur 10, then Dhanmondi → Gulshan → Uttara → Banani
- **Device**: 90%+ mobile (Android dominant) — everything is mobile-first
- **Language**: Bangla primary, English secondary — bilingual with language switcher
- **Communication**: WhatsApp (not email)

### Data Model: Organization → Outlets

- **Organization** (1:1 per user) — business_name, website_url, category, tone_of_voice, brand_keywords
- **Outlet** (many per org) — outlet_name, city, address, google_place_id, facebook_page_url, instagram_handle. Each outlet has independent audits, missions, content, competitors.
- **Tiers**: ফ্রি (Free) = 1 audit + 1 mission, প্রো (Pro) 299 BDT/mo, বিজনেস (Business) 799 BDT/mo, এজেন্সি (Agency) 2,999 BDT/mo

### Competitor Model: Pre-seeded Areas

Competitors are **manually pre-seeded per area** before running ads. Super admin maps 20-30 businesses per area (~3 hours), adds Google Maps + Facebook + Instagram links. Competitor data is cached and refreshed monthly. When a free audit runs, only the owner's data is fetched live — competitor data comes from cache.

## Design System: "The Precision Architect" (Azure Meridian)

The full spec lives in `docs/design-system/azure_meridian/DESIGN.md`. Reference screens (HTML + PNG) are in `docs/design-system/`.

### Key Rules — MUST Follow

- **No borders for layout** — use background color shifts between surface tiers instead of 1px solid borders
- **No divider lines** — use 24-32px gaps instead
- **No `#000000` text** — always use `on-surface` (#191c1e)
- **No sharp corners** — minimum `md` (12px) / `lg` (16px) radius
- **No opaque borders** — if a border is needed for accessibility, use "Ghost Border" (`outline-variant` at 15% opacity)
- **Shadows are ambient** — 40-60px blur, 4-6% opacity, tinted by background color
- **Mobile-first** — design for phone screens first, then scale up

### Color Tokens

| Role | Value |
|---|---|
| `primary` | #0037b0 |
| `primary-container` | #1d4ed8 |
| `surface` (background) | #f7f9fb |
| `surface-container-low` | #f2f4f6 |
| `surface-container-lowest` (cards) | #ffffff |
| `surface-container-high` | #e6e8ea |
| `on-surface` (text) | #191c1e |
| `on-surface-variant` (muted text) | #434655 |
| `outline-variant` (ghost borders) | #c4c5d7 |

### Typography

- **Headlines/Display**: Manrope (extrabold, tight tracking)
- **Body/Labels**: Inter
- Use large size jumps between headline and body for editorial tension

### Signature Patterns

- **Signature Gradient**: `linear-gradient(135deg, #0037b0, #1d4ed8)` for primary CTAs and hero sections
- **Glassmorphism**: semi-transparent surface + `backdrop-blur-md` to `backdrop-blur-xl` for floating nav/overlays
- **Tonal Layering**: depth via stacked surface tiers, not drop shadows

### Icons

Material Symbols Outlined (variable font, default weight 400, FILL 0). Use `FILL 1` for active/selected states.

## App Structure

### Three Navigation Items Only

- **Pilot** (missions) — weekly tasks with ready-made copy-paste content
- **Profile** (settings) — business info, social links, language preference
- **History** (timeline) — week-by-week progress ("Week 1: fixed Google description")

**No dashboards, no graphs, no analytics.** Just: here's what to do, here's the content, do it.

### Free Audit Funnel (No Auth Required)

```
Landing Page → Paste Google Maps Link → Validation Gate → Free Audit Results
→ Soft Gate (email + WhatsApp) → 1 Free Mission → Full Signup → Paid
```

- Validation gate checks basics: name, address, phone, hours, photo, category
- Audit results show: online presence cards + competitor comparison + review analysis
- Soft gate collects email + WhatsApp number after showing results, before showing first mission

### Audit Dimensions

- **Google Maps** (primary, day 1): reviews, photos, description, hours, categories, Q&A, owner reply rate
- **Facebook** (primary for Dhaka, day 1): followers, post frequency, rating, response time, menu, photos
- **Instagram** (secondary, day 1): followers, posts, engagement, reels, bio
- **Website** (secondary, day 1): exists, mobile-friendly, SEO basics, speed, menu, social links
- **YouTube** (future): business mentions, own channel
- **AI Visibility** (future): ChatGPT/Gemini/Perplexity recommendations

### Mission Phases

- **Setup (Weeks 1-5)**: 2-3 missions/week — foundational wins (fix description, upload photos, reply to reviews)
- **Rhythm (Week 6+)**: 1 mission/week + maintenance — ongoing content, seasonal updates, reactive missions
- Variable mission count — sometimes 3, sometimes 0. "Nothing to do this week" builds trust.

## Tech Stack

### Architecture

- **Pattern**: Queue-centric — thin API server, heavy Celery workers
- **API versioning**: All endpoints prefixed with `/api/v1/`

### Backend

- **API**: FastAPI (Python 3.12, venv at `.venv/`)
- **Task queue**: Celery + Redis (broker + result backend + API response cache)
- **Scheduler**: Celery Beat (singleton, staggered per-user audit scheduling)
- **Database**: PostgreSQL via Supabase (10 core tables — organizations, outlets, audits, dimensions, missions, content_drafts, competitors, subscriptions, user_profiles)
- **Auth**: Supabase Auth (JWT verification in FastAPI, credentials never handled server-side). Free audit endpoint requires no auth.
- **AI**: Claude Sonnet 4.6 (audit analysis, mission logic) + Claude Haiku 4.5 (content generation, Bangla + English)

### Frontend

- **App** (`app.growthpilot.com`): React + Vite SPA, React Router v6, TanStack Query + Zustand
- **Landing** (`growthpilot.com`): Bilingual (Bangla/English), mobile-first, "paste your Google Maps link" CTA
- **Shared**: `@growthpilot/ui` package — design tokens, base components
- **Styling**: Tailwind CSS, Google Fonts (Manrope + Inter), Material Symbols Outlined
- **i18n**: react-i18next — all UI strings in translation files, language switcher in header
- **Real-time**: SSE for audit pipeline progress updates

### External APIs

- **SerpApi**: Google Maps rank + competitor discovery
- **Firecrawl**: Website scraping & content audit
- **Facebook Graph API**: Page data (followers, posts, ratings) for business and competitors
- **Instagram Graph API**: Profile data (followers, posts, engagement)
- **YouTube Data API**: Video/channel presence (future)
- **SSLCommerz**: Payments — bKash, Nagad, Visa/Mastercard (~2% transaction fee)
- **WhatsApp Business API**: Notifications, follow-ups, mission alerts

### Deployment

- **Frontend**: Vercel (both app and landing)
- **Backend**: Railway (3 services: API server, Celery worker, Celery Beat)
- **Managed**: Supabase (Postgres + Auth), Redis (Railway addon)

### Monorepo Structure

```
growthpilot/
├── apps/web/          # React + Vite app (mobile-first)
├── apps/landing/      # Landing site (bilingual)
├── packages/ui/       # Shared design system components + tokens
├── backend/           # FastAPI + Celery
├── data/              # Pre-seeded area data (CSVs)
├── pnpm-workspace.yaml
└── turbo.json
```

### MCP

- Stitch (Google's design-to-code MCP server) is configured in `.mcp.json`

## Conventions

- All UI must follow the design system spec — read `DESIGN.md` before building any screen
- Mobile-first — design for phone screens, then scale up
- Bilingual — all user-facing strings go through i18n, never hardcode text
- Use Tailwind utility classes with the custom color tokens defined in `tailwind.config`
- Prefer the reference screen HTML files as the source of truth for component patterns
- API server is a thin read/write layer — no business logic, only enqueue tasks and serve DB results
- All external API calls use the `scrape_with_fallback` pattern (retry 3x, fall back to cached data)
- Celery tasks checkpoint every step to the database for debuggability and SSE progress updates
- Tier enforcement via FastAPI dependency injection (`require_tier()` decorator)
- Outlet ownership verified by joining through Organization (`Organization.user_id == user.id`)
- API routes use `/outlets/{id}` (not brands) — organization settings at `/organizations/me`
- Dev mode (`DEV_MODE=true`) bypasses auth, mocks external APIs, auto-creates tables
- No numerical scores in user-facing UI — focus on actions, not numbers
- Audit result caching: 30-day TTL keyed by Google Maps Place ID
- Rate limiting: 3 free audits per IP per day
