# GrowthPilot — Product Document

> We make local businesses easier to find online — starting with Dhaka restaurants.

---

## 1. The Problem

A café owner in Uttara knows there are a dozen other cafés around them. Some are getting more customers. But they don't know **why**.

They don't know that their competitor has 5,000 Google reviews while they have 30. They don't know that the restaurant down the street has a Foodpanda listing with 4.9★ while they're not on Foodpanda at all. They don't know that their Google Maps listing is using a Facebook page as their website, or that AI assistants like ChatGPT can't find them.

They've maybe heard of SEO, but it means nothing to them. They don't have time to figure it out. They can't afford to hire someone who does.

So they do nothing. And every week they do nothing, the gap between them and the restaurant that figured it out gets wider.

**The core problem:** Local business owners have no way to see how they look online, how they compare to competitors, or what to do about the gaps.

---

## 2. Target Market & Customer Profile

### Primary Market: Dhaka, Bangladesh

**Starting vertical:** Restaurants & cafés

**Future verticals (in order):** Hotels → Travel agencies → Clinics → Coaching centers → Retail/Salons

### Customer Profile

| Attribute | Detail |
|-----------|--------|
| Who | Restaurant/café owner or manager in Dhaka |
| Age range | 25-50 |
| Tech comfort | Comfortable with Facebook, WhatsApp, smartphone. Not comfortable with SEO, Google Business Profile settings, analytics |
| Device | 90%+ mobile (Android dominant) |
| Primary platform | Facebook (this is where their customers find them) |
| Secondary platforms | Google Maps, Instagram, Foodpanda |
| Communication | WhatsApp (not email — email open rates are very low in Bangladesh) |
| Budget for marketing | Low — most spend 0. Some pay a freelancer 2,000-5,000 BDT/month for social media |
| Pain point | "I know I should do something online but I don't know what" |
| Language | Bangla primary, many comfortable in English. App must support both with a language switcher |

### Why Dhaka First

- Founder's home market — language, culture, and network advantage
- Massive gap between where businesses are and where they should be online
- Lower customer acquisition cost through Facebook/Instagram ads
- No GDPR — lighter compliance burden under Bangladesh Digital Security Act
- "Do it for me" value proposition is stronger here — owners want results, not education

---

## 3. The Solution

GrowthPilot is a tool where a business owner can **see their online presence, compare it with competitors, and get told exactly what to do to close the gaps** — with ready-made content they can copy-paste right now.

Three things in sequence: **See yourself. See your competitors. Close the gap.**

The product evolves in three stages:
1. **"Here's what's wrong"** — the audit shows gaps across Google Maps, Website, Social, Delivery platforms *(current focus — built)*
2. **"Here's what to do"** — weekly missions with copy-paste content *(next)*
3. **"We did it for you, just approve"** — one-tap approval for AI-generated content, auto-publishing *(future)*

---

## 4. The Idea

### The Hook: Free Audit

A restaurant owner searches for their business name (autocomplete from our directory) or pastes their Google Maps link. Within seconds, they see:
- **GrowthPilot Score** — a single number out of 5 showing their overall online presence strength
- **Competitor Scorecard** — side-by-side table comparing them with top 3 nearby restaurants
- **How they compare** — you vs area average vs top competitor (reviews + rating)
- **Online presence status** — Google Maps, Website, Menu, Local Presence, AI Search Visibility (green/yellow/red)
- **Social links** — Facebook, Instagram, TikTok, Website (found or missing)
- **Delivery platforms** — Foodpanda, Pathao (listed or missing, with ratings)
- **Where people find them** — TripAdvisor, YouTube, food blogs
- **Menu highlights** — popular items from Google Maps
- **Price positioning** — customer spending distribution
- **Review analysis** — what customers love, what they complain about, actionable suggestions
- **Biggest opportunities** — top gaps sorted by severity

This is the "oh wow" moment that converts visitors into users.

### The Funnel

```
Facebook/Instagram Ad
    ↓
Landing Page (mobile-first, autocomplete search)
    ↓
Search restaurant name OR paste Google Maps link
    ↓
Validation → category check (restaurants only)
    ↓
Audit runs (8 phases, real-time progress via SSE)
    ↓
Full audit report with unique URL (/audit/restaurant-name)
    ↓
Soft Gate — "Get this report on WhatsApp" (name + email + WhatsApp)
    ↓
WhatsApp follow-up with report + improvement tips
    ↓
Full Signup → Paid Conversion
```

### Why This Hook Works

- Zero friction to start — search by name, no signup required
- Autocomplete from pre-crawled directory — instant results for known restaurants
- The competitor comparison creates urgency — "I didn't know I was this far behind"
- The GrowthPilot Score gives a single "oh no" or "nice" moment
- The review analysis creates emotional connection — "this tool understands my business"
- The soft gate comes after value, not before
- Unique shareable URL — owner can bookmark and share the report
- WhatsApp follow-up reaches them where they actually are (not email)

---

## 5. The Product

### 5.1 Audit Engine

The audit engine collects data about the business and their competitors, compares them, and identifies the most impactful gaps.

#### Data Sources

**From Google Maps (via SerpApi place details — 1 API call):**
- Business name, address, rating, review count
- Place ID, coordinates, category/types
- Website URL, phone, menu link
- Business hours, description

**From Enrichment (via SerpApi Google Search — 1 API call per business, done in batch):**
- Social profiles: Facebook URL + followers, Instagram URL + followers, TikTok URL
- Delivery platforms: Foodpanda URL + rating + reviews, Pathao URL
- Directory listings: TripAdvisor, Wanderlog, food blogs
- YouTube mentions
- Menu highlights (popular items)
- Price details (spending distribution)
- Merchant description

**From Website Scraping (via Firecrawl — 1 API call):**
- Content quality (AI-assessed)
- Schema markup presence
- Blog presence
- Internal link structure

**From Google Reviews (via SerpApi Reviews — 1 API call):**
- Recent reviews text
- AI-powered analysis: praised themes, complaints, suggestions, sentiment

**Computed (no API calls):**
- AI Search Visibility score (schema + review quality + NAP consistency + local mentions)
- GrowthPilot Score (weighted average of 10 factors)
- Competitor comparison (you vs area average vs top)
- Gap detection and prioritization

#### Audit Dimensions Shown

1. **Google Maps** — rating, review count, status badge
2. **Menu** — menu link present or missing
3. **Website** — exists, content quality, schema markup
4. **Local Presence** — online mentions count
5. **AI Search Visibility** — can ChatGPT/Google AI find you?

#### Review Analysis

AI-powered analysis of Google Maps review text:
- **Summary**: overall sentiment and key themes
- **Customers love**: top praised aspects (two-column layout)
- **Could improve**: top complaints (two-column layout)
- **Suggestions**: actionable recommendations (separate section)

#### Validation

Before the audit runs, the pipeline checks:
- Is the URL a valid Google Maps link?
- Can we resolve the business (place_id)?
- Is it a restaurant/café? (category allowlist check)

If validation fails, the audit stops and shows a clear message with the rejected category.

### 5.2 Competitor System

#### How It Works Now (Automated)

Competitors are discovered and cached automatically — **no manual pre-seeding required**:

1. **Crawler** (`crawl_serpapi.py`): Searches SerpApi for "restaurant" near a postcode's coordinates. Paginates up to 120 results. Filters by distance (5km max). Saves to `data/crawl/{postcode}/serpapi.json`.

2. **Import** (`import_crawl.py`): Reads crawler JSON, creates records in the `businesses` table with rating, reviews, address, categories, metadata. Generates URL slugs. Idempotent by google_place_id.

3. **Enrichment** (`enrich_serpapi.py`): For each business with 20+ reviews, calls SerpApi Google Search to extract social profiles (Facebook, Instagram, TikTok URLs + follower counts), delivery platform URLs (Foodpanda, Pathao), directory listings, YouTube mentions, menu highlights, price details, merchant description.

4. **During Audit**: Competitors are pulled from the `businesses` table by postcode (same area). Top 10 by review count, excluding the audited business. If no businesses exist for the postcode, falls back to SerpApi nearby search (1 API call).

#### Competitor Data Storage

- All competitor data stored in the `businesses` table
- Enriched data in `metadata` JSON column (social, delivery, directories, menu, price)
- Raw SerpApi response in `cached_data` JSON column
- `enriched` boolean + `enriched_at` timestamp track enrichment status
- URL slug for unique shareable links

#### Area Expansion Playbook (Automated)

1. Add postcode coordinates to `crawl_serpapi.py`
2. Run crawler: `python scripts/crawl_serpapi.py --postcode 1230`
3. Import: `python scripts/import_crawl.py --file data/crawl/1230/serpapi.json`
4. Enrich: `python scripts/enrich_serpapi.py --postcode 1230`
5. Area is ready — businesses appear in autocomplete, audits use cached competitor data

Total time: ~30 minutes + API costs (~$0.50 per postcode)

### 5.3 Mission Engine

*(Not yet rebuilt for MVP-1. Exists in MVP-0 codebase but not connected to the free audit flow.)*

Missions are the core product. Each mission is a specific, actionable task with ready-made content.

#### Mission Types

- **Google Maps missions**: rewrite description, reply to reviews, upload photos, seed Q&A
- **Facebook missions**: post content, update page info
- **Instagram missions**: update bio, post reel ideas
- **Website missions**: create a website, fix SEO issues
- **Review missions**: reply to reviews, set up review collection

#### Setup vs Rhythm Phases

**Setup Phase (Weeks 1-5):** 2-3 missions per week — foundational wins
**Rhythm Phase (Week 6+):** 1 mission per week + reactive missions

### 5.4 User Roles

**Super Admin (us)**
- Run crawler + import + enrichment scripts
- Monitor audit quality
- Manage business directory

**Visitor (anyone)**
- Run free audit (no signup required)
- View full audit results
- Share audit URL
- Submit contact info via soft gate

**Shop Admin (business owner) — future**
- Sign up and claim their business
- View and complete weekly missions
- Manage business profile

### 5.5 The App

#### Landing Page (`/`)

- Hero with autocomplete search (primary) + URL paste fallback
- How it works (3 steps)
- Preview mockup of audit results
- Footer

#### Audit Page (`/audit/{slug}`)

- Unique URL per business (shareable, bookmarkable)
- Real-time pipeline progress tracker (8 phases)
- Full audit report (11 sections)
- Soft gate CTA (name + email + WhatsApp)
- `?renew=true` forces fresh audit
- 404 page for unknown slugs

**Mobile-first.** 2/3 + 1/3 layout on desktop (results + soft gate). Single column on mobile.

**No dashboards, no graphs, no analytics.** Just: here's where you stand, here's what to fix.

---

## 6. Competitive Landscape

*(Unchanged from original — still accurate)*

Nobody is doing "audit + compare + missions + ready-made content" for local businesses in Bangladesh. The market is open.

---

## 7. Business Model & Pricing

### Pricing Tiers

| Tier | Price | What You Get |
|------|-------|-------------|
| **Free** | 0 BDT | 1 full audit with competitor comparison, review analysis, all 11 report sections |
| **Pro** | 299 BDT/mo (~€2.50) | Weekly audits + missions + content + review reply drafts |
| **Business** | 799 BDT/mo (~€6.50) | Everything in Pro + auto-publish + priority support |
| **Agency** | 2,999 BDT/mo (~€25) | Manage 10 businesses from one account |

**Note:** Price points to be validated during MVP-1 WhatsApp conversations.

---

## 8. Acquisition Strategy

*(Unchanged from original — Facebook ads, Facebook groups, Instagram, WhatsApp retention, pre-seeded area data as ad creative. Now enhanced by autocomplete search which removes the friction of finding your restaurant.)*

---

## 9. Data & Caching Strategy

### Business Directory

- Businesses stored in `businesses` table with full details
- Crawled from SerpApi Google Maps (nearby restaurant search)
- Enriched from SerpApi Google Search (social profiles, delivery, directories)
- Each business has a unique URL slug
- Autocomplete search queries this table

### Audit Result Caching

- Full audit results cached in `weekly_audits` + `audit_dimensions` tables
- Cache TTL: 30 days (keyed by google_place_id)
- `?renew=true` bypasses cache
- Cache check only matches audits that completed the full pipeline

### Cost Per Audit

| Scenario | SerpApi | Firecrawl | LLM | Total |
|---|---|---|---|---|
| Enriched business (autocomplete) | 1 (reviews) | 0-1 | 1 | ~$0.01 |
| New business (URL paste) | 1-2 | 0-1 | 1 | ~$0.02 |
| Cached (repeat visit) | 0 | 0 | 0 | $0 |

### Enrichment Cost Per Area

| Step | SerpApi calls | Cost |
|---|---|---|
| Crawler (1 postcode, 6 pages) | 6 | $0.03 |
| Enrichment (45 businesses) | 45 | $0.23 |
| **Total per area** | 51 | **~$0.26** |

---

## 10. Operational Model

### What the team does

| Task | Frequency | Time | Who |
|------|-----------|------|-----|
| Run crawler for new postcode | Per area expansion | 5 min | Script |
| Import crawler data | Per crawl | 1 min | Script |
| Enrich businesses | Per area (45 businesses) | 5 min | Script |
| Re-enrich specific business | As needed | 10 sec | Script |
| Monitor audit quality | Weekly | 30 min | Founder |
| Respond to WhatsApp leads | Daily | Variable | Founder |

### Scaling

| Scale | Approach |
|-------|---------|
| 1-50 leads | Founder handles WhatsApp manually |
| 50-200 leads | Automate WhatsApp follow-ups |
| 200+ leads | Build signup flow, mission engine, paid conversion |

---

## 11. External Services

| Service | Purpose | How we use it | Cost |
|---------|---------|---------------|------|
| **SerpApi** | Google Maps data, Google Search enrichment, reviews | Crawler, enrichment, audit pipeline | ~$0.005/search |
| **Firecrawl** | Website scraping + content analysis | Audit pipeline (website/SEO phase) | ~$0.001/scrape |
| **Ollama (local LLM)** | Review analysis, content quality assessment | Audit pipeline | $0 (self-hosted) |
| **Supabase** | PostgreSQL database, authentication | All data storage | Free tier |
| **Redis** | Celery broker, task queue, caching | Backend task orchestration | Free (Railway addon) |
| **Docker** | Development environment | PostgreSQL, Redis, API, worker, beat | Local only |

### Not yet integrated (from original plan)

| Service | Status | When |
|---------|--------|------|
| Facebook Graph API | Not started | When we add Facebook audit dimension |
| Instagram Graph API | Not started | When we add Instagram audit dimension |
| SSLCommerz | Not started | When paid conversion is built |
| WhatsApp Business API | Not started | When automated follow-ups are built |
| Claude API (Anthropic) | Available but using Ollama | Switch when quality matters more than cost |

---

## 12. Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend (Landing)** | React + Vite SPA, Tailwind CSS |
| **Frontend (App)** | React + Vite SPA, React Router, TanStack Query, Zustand *(MVP-0, not active)* |
| **Shared UI** | `@growthpilot/ui` — Tailwind preset with design tokens |
| **Backend** | FastAPI (Python 3.12), Celery + Redis |
| **Database** | PostgreSQL via Supabase (14 tables) |
| **AI/LLM** | Ollama (kimi-k2.5:cloud) — local, free. Claude API available as upgrade |
| **Authentication** | Supabase Auth *(MVP-0, not used in free audit)* |
| **Hosting** | Docker Compose (local dev). Railway planned for production |
| **Monorepo** | pnpm workspaces + Turborepo |

### Database Tables

| Table | Purpose |
|-------|---------|
| `businesses` | Business directory (crawled + enriched) — 21 columns |
| `competitors` | Comparison targets for specific outlets *(legacy, mostly replaced by businesses)* |
| `weekly_audits` | Audit runs with status, phase progress, cache TTL |
| `audit_dimensions` | Dimension results (raw_data JSON) per audit |
| `soft_leads` | Contact captures from soft gate (name, email, WhatsApp) |
| `seeded_areas` | Manually pre-seeded areas *(legacy, used by seed scripts)* |
| `user_profiles` | User accounts *(MVP-0, not used in free audit)* |
| `organizations` | Business entities *(MVP-0)* |
| `outlets` | Physical locations *(MVP-0)* |
| `missions` | Weekly tasks *(MVP-0)* |
| `content_drafts` | Copy-paste content *(MVP-0)* |
| `subscriptions` | Billing *(MVP-0)* |

### Scripts

| Script | Purpose |
|--------|---------|
| `crawl_serpapi.py` | Discover restaurants in a postcode via SerpApi |
| `import_crawl.py` | Import crawler JSON into businesses table |
| `enrich_serpapi.py` | Enrich businesses with social profiles, delivery URLs, menu, price |
| `seed_area.py` | Manually seed competitor data from CSV *(legacy)* |
| `audit_area.py` | Run Google Maps scrape for seeded competitors *(legacy)* |

---

## 13. Roadmap

### MVP-0: Engine Built ✅ (Done — April 2026)

- Full audit pipeline: Google Maps, Website/SEO, Local Authority, YouTube, AI Readiness
- Review analysis with AI
- Competitor discovery
- Mission generation + content drafts
- Multi-location support
- Supabase auth, Docker dev setup

### MVP-1: The Hook Works ✅ (Built — April 2026)

**What's done:**
- Landing page with autocomplete search + URL paste fallback
- Free audit endpoint (no auth) with category validation
- 8-phase audit pipeline with real-time SSE progress
- Auto-competitor discovery by postcode (from businesses table)
- Website/SEO analysis via Firecrawl + LLM
- Review analysis via SerpApi + LLM
- AI Search Visibility scoring
- GrowthPilot Score (0-5, 10 weighted factors)
- Competitor Scorecard (side-by-side table)
- Social Links (Facebook/Instagram/TikTok with follower counts)
- Delivery Platforms (Foodpanda/Pathao with ratings)
- Menu Highlights + Price Positioning
- 30-day audit caching with `?renew=true` override
- Unique shareable URLs (`/audit/restaurant-name`)
- Soft gate lead capture (name + email + WhatsApp → soft_leads table)
- Business directory with crawler + import + enrichment pipeline
- 78 businesses crawled and enriched for Uttara (postcode 1230)

**What's NOT done (deferred):**
- Bilingual (Bangla/English) — English only for now
- Facebook/Instagram audit dimensions — only Google Maps data
- SSLCommerz payments — no paid tier yet
- WhatsApp Business API — manual follow-up for now
- Mission engine connected to free audit — missions exist in MVP-0 but not in the new flow
- Rate limiting — not implemented yet
- Facebook Pixel + analytics — not set up

### MVP-2: They Pay (Next)

**Goal:** 50 paying customers at 299 BDT/mo

- Connect mission engine to free audit results
- Signup flow (Supabase Auth)
- SSLCommerz payment integration
- WhatsApp automated follow-ups
- Expand to 5 postcodes (Dhanmondi, Gulshan, Banani, Mirpur)
- Bilingual support (Bangla/English)

### Alpha: They Come Back

**Goal:** 200+ users, 25% weekly retention

- Weekly recurring audits
- Reactive missions ("1-star review alert", seasonal triggers)
- Facebook + Instagram audit dimensions
- Review reply templates
- Referral program

---

## 14. Metrics That Matter

| Phase | North Star | Target |
|-------|-----------|--------|
| MVP-1 | Do they try it? | 100 free audits, 20 soft leads |
| MVP-2 | Will they pay? | 50 paying at 299 BDT/mo |
| Alpha | Do they come back? | 25% weekly retention |
| Beta | Do they tell others? | 30% organic signup rate |
| GA | Is it profitable? | LTV > 10x CAC |

---

## 15. What We're NOT Building

- No social media scheduling tool
- No CRM / customer management
- No email marketing platform
- No POS / payment / ordering system
- No food delivery integration
- No generic AI chatbot
- No booking / reservation system

**We do ONE thing:** Make local businesses easier to find online.

---

## 16. Key Decisions Made During MVP-1

| Decision | Why |
|---|---|
| Autocomplete search over URL-only input | Lower friction — owner doesn't need to find their Google Maps link |
| Auto-discovery over manual pre-seeding | Scales without 3 hours of manual work per area |
| SerpApi over Google APIs directly | Simpler integration, no API key management, rich data (knowledge graph) |
| Businesses table separate from competitors | Directory of all businesses vs comparison targets for specific users |
| Enrichment as a batch process | One-time cost per business, data reused across all audits |
| Local LLM (Ollama) over Claude API | Zero cost during development, switch to Claude when quality matters |
| No scores in user-facing UI | Focus on actions not numbers — except GrowthPilot Score which is the hook |
| Social pages from Google, not auto-detected | Don't guess wrong social links — show what Google knows |
| Unique URLs per business | Shareable, bookmarkable, SEO-friendly audit reports |
| Soft gate = "Get report on WhatsApp" not "claim ownership" | Can't verify ownership from a free audit — qualify later via WhatsApp |

---

*Last updated: April 4, 2026*
*Document version: 3.0 — MVP-1 built*
