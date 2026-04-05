# GrowthPilot Database Schema

12 tables. PostgreSQL via Supabase.

---

## Relationships

```
user_profiles 1──1 organizations 1──∞ outlets 1──∞ competitors (nullable FK)
                                       │ 1──∞ weekly_audits 1──∞ audit_dimensions
                                       │           │ 1──∞ missions 1──∞ content_drafts
                                       │           │ 1──∞ soft_leads
user_profiles 1──1 subscriptions
seeded_areas 1──∞ competitors (nullable FK)
```

---

## user_profiles

User accounts linked to Supabase Auth.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| supabase_uid | varchar | not null | unique, indexed |
| email | varchar | not null | |
| tier | varchar | not null | `free` \| `pro` \| `business` \| `agency` |
| whatsapp_number | varchar | nullable | primary notification channel |
| language | varchar | not null | `en` \| `bn` \| expandable |
| created_at | timestamptz | not null | |

---

## organizations

One organization per user. Holds business identity.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| user_id | uuid | not null | FK → user_profiles, unique |
| business_name | varchar | not null | |
| website_url | varchar | not null | |
| category | varchar | not null | e.g. "restaurant", "hotel" |
| tone_of_voice | varchar | nullable | |
| brand_keywords | json | nullable | |
| created_at | timestamptz | not null | |

---

## outlets

Physical locations belonging to an organization.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| organization_id | uuid | not null | FK → organizations |
| outlet_name | varchar | not null | |
| city | varchar | not null | |
| address | varchar | nullable | |
| google_place_id | varchar | nullable | |
| maps_url | varchar | nullable | Google Maps link |
| facebook_page_url | varchar | nullable | |
| instagram_handle | varchar | nullable | |
| area | varchar | nullable | e.g. "mirpur-10", "dhanmondi" |
| next_audit_at | timestamptz | nullable | scheduled next audit |
| created_at | timestamptz | not null | |

---

## weekly_audits

Audit runs — both free (no auth) and recurring (linked to outlet).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| outlet_id | uuid | **nullable** | FK → outlets. Null for free audits |
| google_place_id | varchar | nullable | cache key for free audits, indexed |
| is_free_audit | boolean | not null | |
| week_number | integer | not null | |
| status | varchar | not null | `pending` \| `running` \| `completed` \| `failed` |
| current_phase | varchar | nullable | SSE progress tracking |
| total_score | integer | nullable | internal only, not shown in UI |
| score_delta | integer | nullable | |
| phase_progress | json | nullable | per-phase progress for SSE |
| created_at | timestamptz | not null | |
| completed_at | timestamptz | nullable | |
| expires_at | timestamptz | nullable | 30-day cache TTL |

---

## audit_dimensions

Individual dimension results within an audit. Dimension values are strings — new dimensions (facebook, instagram) are just new rows.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| audit_id | uuid | not null | FK → weekly_audits |
| dimension | varchar | not null | `google_maps` \| `facebook` \| `instagram` \| `website` \| `youtube` \| `ai_visibility` |
| score | integer | not null | internal scoring |
| weight | float | not null | |
| is_stale | boolean | not null | |
| raw_data | json | nullable | full scraped data |

---

## missions

Actionable tasks generated from audit gaps. Each mission has copy-paste content via content_drafts.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| audit_id | uuid | not null | FK → weekly_audits |
| outlet_id | uuid | not null | FK → outlets |
| title | varchar | not null | |
| description | text | not null | |
| channel | varchar | not null | e.g. "google_maps", "facebook", "instagram" |
| impact_score | integer | not null | internal prioritization |
| difficulty | varchar | not null | `easy` \| `medium` \| `hard` |
| estimated_minutes | integer | not null | |
| status | varchar | not null | `pending` \| `in_progress` \| `completed` \| `skipped` |
| sort_order | integer | not null | display order |
| priority_score | float | nullable | |

---

## content_drafts

Copy-paste ready content attached to missions.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| mission_id | uuid | not null | FK → missions |
| channel | varchar | not null | |
| title | varchar | not null | |
| body | text | not null | the actual copy-paste content |
| metadata | json | nullable | hashtags, photo tips, etc. |
| copy_count | integer | not null | tracks how many times user copied |

---

## competitors

Pre-seeded by super admin per area, or auto-discovered by the free audit pipeline. Cached by postcode for 30 days.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| outlet_id | uuid | **nullable** | FK → outlets. Null for area-level competitors |
| seeded_area_id | uuid | nullable | FK → seeded_areas, indexed. For manually seeded only |
| business_name | varchar | not null | |
| google_place_id | varchar | nullable | |
| maps_url | varchar | nullable | |
| website_url | varchar | nullable | |
| facebook_page_url | varchar | nullable | |
| instagram_handle | varchar | nullable | |
| area | varchar | nullable | legacy area grouping |
| postcode | varchar | nullable | indexed. Used for auto-discovery caching (e.g. "1230") |
| lat | float | nullable | latitude from SerpApi |
| lng | float | nullable | longitude from SerpApi |
| source | varchar | not null | `manual` \| `auto` |
| cached_data | json | nullable | cached Google Maps data (rating, reviews, address, types) |
| cached_at | timestamptz | nullable | for 30-day cache TTL |
| gap_analysis | json | nullable | |

---

## subscriptions

Billing via SSLCommerz (bKash, Nagad, cards).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| user_id | uuid | not null | FK → user_profiles, unique |
| sslcommerz_transaction_id | varchar | nullable | |
| plan | varchar | not null | `free` \| `pro` \| `business` \| `agency` |
| status | varchar | not null | `active` \| `past_due` \| `cancelled` |
| current_period_end | timestamptz | nullable | |

---

## soft_leads

Captures from the free audit soft gate (email + WhatsApp) before full signup.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| email | varchar | not null | |
| whatsapp_number | varchar | not null | |
| google_place_id | varchar | not null | indexed |
| audit_id | uuid | nullable | FK → weekly_audits |
| area | varchar | nullable | |
| converted | boolean | not null | true when they sign up |
| created_at | timestamptz | not null | |

---

## seeded_areas

Tracks which areas have been pre-seeded with competitor data and are ready for ads.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| **id** | uuid | PK | |
| name | varchar | not null | unique. e.g. "mirpur-10", "gulshan" |
| city | varchar | not null | e.g. "dhaka", "chittagong" |
| business_count | integer | not null | number of businesses seeded |
| status | varchar | not null | `seeding` \| `ready` \| `active` |
| seeded_at | timestamptz | not null | |
| last_refreshed_at | timestamptz | nullable | monthly refresh tracking |
