# GrowthPilot System Architecture Design

**Date:** 2026-04-01
**Status:** Approved
**Scope:** Full system architecture — how all services connect, communicate, and deploy

---

## 1. Architecture Overview

GrowthPilot uses a **queue-centric architecture** where the API server is a thin read/write layer and all heavy computation runs in Celery workers. PostgreSQL (Supabase) is the single source of truth. Redis serves as the Celery broker and API response cache for graceful degradation.

### Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Stack | FastAPI + Celery + Redis + Supabase (Postgres) | Python ecosystem, async-ready, managed Postgres with auth |
| Deployment | Split minimal — Vercel (frontends) + Railway (API + worker) | Frontend deploys independently, worker scales without blocking API |
| Audit cycle | Staggered per-user based on onboard time | Spreads API load evenly, no thundering herd |
| AI prompt chain | DAG with checkpoints | Parallel data gathering, sequential analysis, retry at step level |
| Real-time updates | Server-Sent Events (SSE) | Server-to-client only, native browser support, trivial in FastAPI |
| API failure handling | Retry 3x + cached fallback + stale flag | User always gets a full score; stale dimensions flagged in UI |
| API versioning | `/api/v1/` prefix on all endpoints | Low cost now, avoids painful migration on breaking changes |
| Competitor discovery | Auto (SerpApi) + user can swap 1 of 3 | Fully automatic by default, personal override for relevance |

---

## 2. Service Topology & Deployment

Four deployed services + two managed services.

### Vercel

**React + Vite SPA** (`app.growthpilot.com`)
- Static build, CDN-distributed
- Tailwind CSS, Manrope/Inter fonts, Material Symbols Outlined
- Communicates with API via REST + SSE

**Next.js SSG** (`growthpilot.com`)
- Static export, marketing/landing site
- MDX for blog posts, full SEO (meta tags, structured data, sitemap)

### Railway (3 services)

**API Server** (FastAPI)
- Handles auth (Supabase JWT verification), REST endpoints, SSE streams
- No business logic — enqueues tasks, serves DB results
- 1 instance, scales to 2+

**Celery Worker**
- Runs all audit pipeline tasks: scraping, API calls, Claude prompts, content generation
- Checkpoints every step to DB
- 1 instance, scales to 3+

**Celery Beat**
- Scheduler singleton
- Reads `next_audit_at` per brand_profile, enqueues audit pipelines at the right time
- Also handles notification dispatch timing

### Managed Services

**Supabase** — PostgreSQL database + Auth (email + social login, JWT)

**Redis** (Railway addon) — Celery message broker + result backend + API response cache

### Connections

- React → API: HTTPS REST + SSE (auth via Supabase JWT in Authorization header)
- API → Redis: Enqueue Celery tasks (via `.delay()` / `.apply_async()`)
- Worker → Redis: Consume tasks, publish results
- Worker → PostgreSQL: Checkpoint intermediate results, write final outputs
- Worker → External APIs: SerpApi, Firecrawl, Otterly, Reddit, YouTube, Claude
- Beat → Redis: Enqueue scheduled audit pipelines
- API → PostgreSQL: Read audit results, scores, missions, content for frontend

**Key principle:** The API server is a thin read/write layer. All heavy computation happens in workers. The API stays fast and responsive regardless of how many audits are running.

---

## 3. Audit Pipeline DAG

The weekly audit runs as a Celery chord + chain — parallel data gathering, then sequential analysis, then parallel content generation.

### Phase 1 — Data Gathering (parallel, Celery chord)

7 tasks run simultaneously. Each writes results to `platform_scores` or `competitor_data`:

| Task | External API | Data collected |
|---|---|---|
| `scrape_google_maps` | SerpApi | Rank position, profile completeness, photos, Q&A, categories |
| `scrape_website` | Firecrawl | FAQ, About page, schema markup, page speed, content freshness |
| `scrape_social` | Meta Graph API + LinkedIn | Posting frequency, engagement metrics |
| `scrape_reddit` | Reddit API | Mentions in local subreddits, thread activity |
| `scrape_youtube` | YouTube Data API | Title, description, transcript quality, chapter markers |
| `fetch_ai_citations` | Otterly.AI | Mentions in ChatGPT, Perplexity, Google AIO, Gemini, Copilot |
| `discover_competitors` | SerpApi | Top 3 businesses in same category + city, then scrapes each |

All Phase 1 tasks use the `scrape_with_fallback` pattern — retry 3x, then fall back to cached data from the last successful run.

### Phase 2 — Analysis (sequential, Claude Sonnet)

Runs after all Phase 1 tasks complete:

1. **`compute_visibility_score`** — Reads all `platform_scores`, applies weighted formula, produces composite score (0-100) + per-dimension breakdown. Writes to `weekly_audits`.
2. **`analyze_competitor_gaps`** — Claude Sonnet compares user scores vs competitor scores across 5 gap dimensions. Writes to `competitor_gaps`.
3. **`generate_missions`** — Claude Sonnet selects top 3 actions ranked by impact x ease. Considers user history (no repeated missions within 4 weeks). Writes to `weekly_missions`.

### Phase 3 — Content Factory (parallel per mission, Claude Haiku)

Each mission gets its own `generate_content` task running in parallel. Produces all relevant channel assets (Google Biz description, Instagram caption, Facebook post, Reddit reply drafts, etc.). Writes to `content_drafts`.

If one mission's content generation fails, the other two still deliver. Failed mission marked as `content_status: failed`.

### Phase 4 — Notify

`send_notification` — Telegram bot message + Resend email: "Your Week N missions are ready. Visibility Score: X (+Y from last week)."

### Celery Expression (pseudocode)

```python
pipeline = (
    chord(
        [scrape_google_maps, scrape_website, scrape_social,
         scrape_reddit, scrape_youtube, fetch_ai_citations,
         discover_competitors],       # Phase 1: parallel
        compute_visibility_score.si() # Phase 2.1: after all complete
    )
    | analyze_competitor_gaps.si()    # Phase 2.2: sequential
    | generate_missions.si()          # Phase 2.3: sequential
    | chord(
        [generate_content.s(i) for i in range(3)],  # Phase 3: parallel per mission
        send_notification.si()        # Phase 4: after all content ready
    )
)

pipeline.apply_async(args=[user_id, audit_week_id])
```

### Failure & Degradation Rules

- **Phase 1 task fails after 3 retries:** Use cached data from last successful run (Redis, TTL 14 days). Flag dimension as stale in `platform_scores`. Pipeline continues.
- **Phase 2 Claude call fails:** Retry 3x with exponential backoff (5s, 30s, 120s). If still failing, delay pipeline by 1 hour and retry entire phase.
- **Phase 3 content generation fails:** Retry per-mission independently. Other missions still deliver. Mark failed mission as `content_status: failed`.
- **Competitor discovery fails:** Skip competitor gap analysis. Missions generated from user's own audit data only. Note in UI: "Competitor data unavailable this week."

---

## 4. Real-Time Dashboard Updates

The dashboard shows pipeline status at all times via SSE.

### How It Works

1. User opens dashboard → API reads current audit state from DB
2. If audit is in progress, frontend opens SSE connection to `/api/v1/audits/{audit_id}/stream`
3. Celery workers checkpoint progress to DB (`phase_progress` JSONB field on `weekly_audits`)
4. API polls DB and pushes SSE events: `{"phase": 1, "task": "scrape_reddit", "status": "completed", "progress": "5/7"}`
5. Frontend updates progress indicator in real time via custom `useAuditStream` hook

### Dashboard States

| Audit Status | User sees |
|---|---|
| `scheduled` | "Your next audit runs on Tuesday" with countdown |
| `in_progress` — Phase 1 | "Gathering data..." with progress (e.g., 4/7 sources complete) |
| `in_progress` — Phase 2 | "Analyzing your visibility..." |
| `in_progress` — Phase 3 | "Writing your content..." |
| `completed` | Full dashboard — score, missions, content ready to copy |
| `partial` | Dashboard with stale dimensions flagged: "Reddit data from last week" |
| `failed` | "Something went wrong. Retrying in 1 hour." with support link |

---

## 5. Data Model

PostgreSQL (Supabase) — 9 core tables.

### Identity

**`users`**
- `id` (uuid, PK) — Supabase Auth
- `email`
- `tier` (free | pro | agency)
- `telegram_chat_id` (nullable)
- `notification_prefs` (jsonb)
- `created_at` / `updated_at`

**`brand_profiles`**
- `id` (uuid, PK)
- `user_id` (FK → users)
- `business_name`
- `website_url`
- `category` (e.g. "restaurant")
- `city`
- `tone_of_voice` (jsonb)
- `brand_keywords` (text[])
- `google_place_id` (nullable)
- `next_audit_at` (timestamptz)
- `created_at` / `updated_at`

Agency users have multiple brand_profiles. Free/Pro users have one.

### Weekly Audit Cycle

**`weekly_audits`**
- `id` (uuid, PK)
- `brand_id` (FK → brand_profiles)
- `week_number` (int)
- `status` (scheduled | in_progress | completed | partial | failed)
- `phase` (1 | 2 | 3 | 4)
- `phase_progress` (jsonb) — e.g. `{"scrape_reddit": "completed"}`
- `visibility_score` (int, 0-100)
- `score_breakdown` (jsonb) — per-dimension scores
- `previous_score` (int) — for delta display
- `started_at` / `completed_at`
- `created_at`

**`platform_scores`**
- `id` (uuid, PK)
- `audit_id` (FK → weekly_audits)
- `brand_id` (FK → brand_profiles)
- `platform` (google_maps | website | social | reddit | youtube | ai_citations)
- `raw_data` (jsonb) — full API response
- `score` (int, 0-100)
- `is_stale` (boolean) — true if from cache
- `stale_from_audit_id` (FK, nullable)
- `scraped_at` (timestamptz)

One row per platform per audit.

### Competitor Intelligence

**`competitors`**
- `id` (uuid, PK)
- `brand_id` (FK → brand_profiles)
- `business_name`
- `google_place_id`
- `website_url` (nullable)
- `source` (auto | manual) — tracks how the competitor was added
- `discovered_at`

Top 3 per brand. User can swap 1 auto-discovered for a manual pick.

**`competitor_scores`**
- `id` (uuid, PK)
- `audit_id` (FK → weekly_audits)
- `competitor_id` (FK → competitors)
- `platform` (same enum as platform_scores)
- `score` (int, 0-100)
- `raw_data` (jsonb)
- `scraped_at`

**`competitor_gaps`**
- `id` (uuid, PK)
- `audit_id` (FK → weekly_audits)
- `competitor_id` (FK → competitors)
- `dimension` (reviews | google_biz | website | social_reddit | reply_rate)
- `user_value` (int)
- `competitor_value` (int)
- `gap_score` (int)
- `analysis` (text) — Claude's explanation

### Missions & Content

**`weekly_missions`**
- `id` (uuid, PK)
- `audit_id` (FK → weekly_audits)
- `brand_id` (FK → brand_profiles)
- `rank` (1 | 2 | 3)
- `title` (text)
- `description` (text)
- `impact_score` (int, 1-10)
- `difficulty` (low | medium | high)
- `estimated_minutes` (int)
- `target_dimension` (platform enum)
- `status` (pending | active | completed | skipped)
- `content_status` (pending | generating | ready | failed)
- `completed_at` (nullable)

**`content_drafts`**
- `id` (uuid, PK)
- `mission_id` (FK → weekly_missions)
- `channel` (google_biz | instagram | facebook | reddit | linkedin | youtube | whatsapp | website | blog)
- `title` (text, nullable)
- `body` (text) — the actual content
- `metadata` (jsonb) — hashtags, timing recommendations, etc.
- `copy_count` (int, default 0) — tracks usage
- `created_at`

Multiple rows per mission (one per channel).

### Billing

**`subscriptions`**
- `id` (uuid, PK)
- `user_id` (FK → users)
- `stripe_customer_id`
- `stripe_subscription_id`
- `tier` (pro | agency)
- `status` (active | past_due | cancelled)
- `current_period_end` (timestamptz)
- `created_at` / `updated_at`

### Key Relationships

- `users` 1 → N `brand_profiles` (1 for free/pro, unlimited for agency)
- `brand_profiles` 1 → N `weekly_audits` (one per week)
- `weekly_audits` 1 → N `platform_scores` (6 per audit — one per platform)
- `brand_profiles` 1 → N `competitors` (up to 3)
- `weekly_audits` 1 → N `competitor_scores` (up to 18 — 6 platforms x 3 competitors)
- `weekly_audits` 1 → N `competitor_gaps` (up to 15 — 5 dimensions x 3 competitors)
- `weekly_audits` 1 → 3 `weekly_missions`
- `weekly_missions` 1 → N `content_drafts` (up to 9 — one per channel)

### Critical Indexes

- `brand_profiles(next_audit_at)` — Beat scheduler queries this every minute
- `weekly_audits(brand_id, week_number)` UNIQUE — prevent duplicate audits
- `weekly_audits(brand_id, status)` — dashboard loads latest active/completed audit
- `platform_scores(audit_id, platform)` UNIQUE — one score per platform per audit
- `content_drafts(mission_id, channel)` UNIQUE — one draft per channel per mission

---

## 6. API Endpoints

FastAPI — thin read/write layer. All endpoints prefixed with `/api/v1/`. All require valid Supabase JWT in `Authorization: Bearer {jwt}` header (except Stripe webhook).

### Auth

Auth is fully managed by Supabase (signup, login, social, password reset). The React app uses `@supabase/supabase-js` directly. FastAPI only verifies JWTs — it never handles credentials.

### Onboarding

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/brands` | Create brand profile. Triggers async website scrape to infer tone. Returns brand_id. |
| PATCH | `/api/v1/brands/{brand_id}` | Update brand profile — tone, keywords, category. Used by onboarding + settings. |
| POST | `/api/v1/brands/{brand_id}/audit` | Trigger first audit immediately. Enqueues full pipeline to Celery. Returns audit_id. |

### Dashboard & Audit

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/brands/{brand_id}/dashboard` | Aggregated dashboard payload: latest audit, active missions, next audit time. Single query. |
| GET | `/api/v1/audits/{audit_id}/stream` | SSE endpoint. Streams phase_progress updates in real-time. Closes on completion. |
| GET | `/api/v1/brands/{brand_id}/scores/history` | Score history for progress chart. Pro/agency only. |

### Missions & Content

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/audits/{audit_id}/missions` | List 3 missions with status, impact, difficulty, estimated time. |
| PATCH | `/api/v1/missions/{mission_id}` | Update mission status: active, completed, skipped. |
| GET | `/api/v1/missions/{mission_id}/content` | All content drafts for a mission. |
| POST | `/api/v1/content/{content_id}/copied` | Track content copy event. Increments copy_count. |

### Competitors

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/brands/{brand_id}/competitors` | List competitors with source, scores, gap analysis. |
| PUT | `/api/v1/brands/{brand_id}/competitors/{competitor_id}/swap` | Replace auto-discovered competitor with manual pick. Max 1 swap. |

### Billing

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/billing/checkout` | Create Stripe Checkout session for upgrade. Returns session URL. |
| POST | `/api/v1/billing/webhook` | Stripe webhook receiver. Processes subscription lifecycle events. |
| POST | `/api/v1/billing/portal` | Create Stripe Customer Portal session for self-service management. |

### Tier Enforcement

Enforced via FastAPI dependency injection — a `require_tier(min_tier)` decorator on protected endpoints:

- **Free:** 1 brand, 1 audit (no recurring), score only (missions/content return 403 with upgrade prompt)
- **Pro:** 1 brand, weekly audits, full missions + content, 1 competitor swap
- **Agency:** Unlimited brands, weekly audits per brand, full features, 1 competitor swap per brand

---

## 7. Frontend Architecture

Two separate frontends sharing a design system.

### App — React + Vite (`app.growthpilot.com`)

- **Router:** React Router v6
- **State:** TanStack Query (server state) + Zustand (UI state only)
- **Auth:** Supabase JS client → JWT in headers
- **Styling:** Tailwind CSS + design tokens from Azure Meridian
- **SSE:** Custom `useAuditStream(auditId)` hook wrapping EventSource, feeds directly into TanStack Query cache
- **Deploy:** Vercel (static build)

**Routes:**
- `/onboarding/find-business`
- `/onboarding/brand-voice`
- `/onboarding/generating-plan`
- `/dashboard`
- `/missions/:missionId`
- `/missions/:missionId/content`
- `/competitors`
- `/analytics` (score history)
- `/settings/brand-identity`
- `/settings/billing`

### Landing — Next.js SSG (`growthpilot.com`)

- **Mode:** Static export (`output: export`)
- **Styling:** Tailwind CSS + same design tokens
- **Content:** MDX for blog posts
- **SEO:** Full meta tags, structured data, sitemap
- **Deploy:** Vercel

**Pages:**
- `/` (hero + features + pricing)
- `/pricing`
- `/blog`
- `/blog/:slug`
- `/about`
- `/legal/privacy`
- `/legal/terms`

### Shared Package — `@growthpilot/ui`

Shared between both frontends via monorepo workspace:

- **Design Tokens:** Tailwind preset (colors, typography, spacing, radii from Azure Meridian spec)
- **Base Components:** Button, Card, Input, Badge, Score indicator
- **Fonts & Icons:** Manrope + Inter config, Material Symbols Outlined setup

### Monorepo Structure

```
growthpilot/
├── apps/
│   ├── web/               # React + Vite (app.growthpilot.com)
│   │   ├── src/
│   │   │   ├── routes/    # React Router pages
│   │   │   ├── hooks/     # useAuditStream, useAuth, etc.
│   │   │   ├── api/       # API client (fetch wrappers)
│   │   │   └── store/     # Zustand stores
│   │   └── vite.config.ts
│   │
│   └── landing/           # Next.js SSG (growthpilot.com)
│       ├── app/           # Next.js app router pages
│       ├── content/       # MDX blog posts
│       └── next.config.ts
│
├── packages/
│   └── ui/                # @growthpilot/ui — shared components + tokens
│       ├── components/    # Button, Card, Input, Badge, etc.
│       ├── tailwind/      # Shared Tailwind preset (colors, fonts, radii)
│       └── index.ts
│
├── backend/               # FastAPI + Celery (separate deploy)
│   ├── app/
│   │   ├── api/v1/        # Route handlers
│   │   ├── core/          # Config, auth, dependencies
│   │   ├── models/        # SQLAlchemy models
│   │   ├── tasks/         # Celery tasks (pipeline)
│   │   └── services/      # External API wrappers
│   └── pyproject.toml
│
├── pnpm-workspace.yaml    # Frontend monorepo workspace
└── turbo.json             # Turborepo for build orchestration
```

---

## 8. External Integrations & Caching

### External API Summary

| API | Used by | Calls/user/week | Cost | Cache TTL | Degradation |
|---|---|---|---|---|---|
| SerpApi | scrape_google_maps, discover_competitors | ~4 | $0.20/week | 7 days | Last week's rank data |
| Firecrawl | scrape_website | 1 | $0.01 | 14 days | Last cached crawl |
| Otterly.AI | fetch_ai_citations | 1 batch | $0.40/month | 7 days | Last week's citations |
| Reddit API | scrape_reddit | ~5 | Free | 7 days | Last cached mentions |
| YouTube Data API | scrape_youtube | ~3 | Free | 7 days | Last cached video data |
| Claude API (Sonnet) | analyze_competitor_gaps, generate_missions | 2 | ~$0.10/week | N/A | Retry → delay 1hr |
| Claude API (Haiku) | generate_content (x3) | 3 | ~$0.07/week | N/A | Retry per mission |
| Telegram Bot API | send_notification | 1 | Free | N/A | Fall back to email |
| Resend | send_notification (email) | 1 | ~$0.01 | N/A | Log and skip |
| Stripe | billing/webhook | Event-driven | 2.9% + $0.30 | N/A | Webhook retry (Stripe-managed) |

**Total variable cost per Pro user per month: ~$1.53**

### Redis Caching Strategy

**Layer 1 — API response cache:**
Raw responses from SerpApi, Firecrawl, Reddit, YouTube, Otterly. Keyed by `api:{provider}:{brand_id}`. TTL 7-14 days. Used for graceful degradation when external APIs fail.

**Layer 2 — Celery broker + results:**
Task queue messages and short-lived results. Managed internally by Celery. TTL: minutes to hours.

**Layer 3 — Dashboard cache:**
Pre-computed dashboard payload per brand. Keyed by `dash:{brand_id}`. Invalidated when new audit completes. Avoids re-aggregating on every page load.

### Unified Degradation Pattern

```python
async def scrape_with_fallback(
    provider: str,
    brand_id: str,
    scrape_fn: Callable
) -> ScrapedData:
    try:
        data = await retry(scrape_fn, max=3)
        redis.set(f"api:{provider}:{brand_id}", data, ttl=CACHE_TTLS[provider])
        return ScrapedData(data=data, is_stale=False)
    except ExternalAPIError:
        cached = redis.get(f"api:{provider}:{brand_id}")
        if cached:
            return ScrapedData(data=cached, is_stale=True)
        return ScrapedData(data=None, is_stale=True)
```

### Notification Integrations

**Telegram Bot API:** User links Telegram in settings via OAuth-style deep link. Bot sends weekly message with score and link to dashboard.

**Resend (Email):** Transactional emails — welcome sequence, weekly audit ready, subscription receipts. HTML templates styled with design system.

**Stripe Webhooks:** Inbound integration processing subscription lifecycle events (checkout.session.completed, invoice.paid, customer.subscription.updated/deleted). Updates user tier in DB.

### Cost Optimization

- **Claude Batch API** for all overnight audit runs — 50% cost reduction
- **Prompt caching** for system prompts (identical across users) — 90% saving on cached tokens
- **Competitor persistence** — competitors stored across audits, not re-discovered weekly (saves SerpApi calls)
- **Firecrawl 14-day cache** — websites change slowly, no need for weekly re-crawl unless score drops
