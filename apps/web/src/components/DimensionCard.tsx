import ScoreRing from "./ScoreRing";

// ─── Types ────────────────────────────────────────────────────────────────────

interface GoogleMapsRaw {
  position?: number;
  rating?: number;
  reviews?: number;
  title?: string;
  place_id?: string;
}

interface WebsiteRaw {
  content?: string;
  title?: string;
  description?: string;
  links?: string[];
  has_schema?: boolean | null;
  has_blog?: boolean | null;
  content_quality?: {
    quality: "high" | "medium" | "low";
    summary?: string;
    has_business_info?: boolean;
    has_contact_info?: boolean;
    has_product_details?: boolean;
    has_clear_cta?: boolean;
  } | null;
  error?: string | null;
}

interface LocalAuthorityRaw {
  mention_count?: number;
  sources?: { title: string; url: string; snippet: string }[];
  on_best_of_list?: boolean;
}

interface YouTubeRaw {
  video_count?: number;
  videos?: { title: string; channel: string }[];
  has_own_channel?: boolean;
}

interface AIReadinessRaw {
  has_schema?: boolean | null;
  review_keywords?: boolean;
  review_quality?: "high" | "medium" | "low" | null;
  nap_consistent?: boolean;
  local_mentions?: number;
}

type RawData =
  | GoogleMapsRaw
  | WebsiteRaw
  | LocalAuthorityRaw
  | YouTubeRaw
  | AIReadinessRaw
  | Record<string, unknown>
  | null
  | undefined;

export interface Dimension {
  dimension: string;
  score: number;
  weight: number;
  is_stale: boolean;
  raw_data?: RawData;
}

// ─── Criterion helpers ────────────────────────────────────────────────────────

export interface Criterion {
  label: string;
  met: boolean;
  unknown?: boolean;  // true = API call failed, could not verify
  points: number;
  note?: string;
}

export function getStatusLabel(score: number): { label: string; color: string } {
  if (score >= 70) return { label: "Good", color: "text-primary" };
  if (score >= 40) return { label: "Needs work", color: "text-yellow-600" };
  return { label: "Critical", color: "text-red-500" };
}

// ─── Per-dimension breakdown logic ────────────────────────────────────────────

function getGoogleMapsCriteria(raw: GoogleMapsRaw): {
  criteria: Criterion[];
  highlights: string[];
  tip: string;
} {
  const position = raw.position ?? null;
  const rating = raw.rating ?? null;
  const reviews = raw.reviews ?? null;

  const criteria: Criterion[] = [
    {
      label:
        position !== null && position <= 3
          ? `Maps position #${position}`
          : position !== null && position <= 10
            ? `Maps position #${position} (top 10)`
            : "No top-10 Maps position found",
      met: position !== null && position <= 10,
      points: position !== null && position <= 3 ? 50 : position !== null && position <= 10 ? 30 : 0,
      note:
        position !== null && position > 3 && position <= 10
          ? "Reach top-3 for +20 more pts"
          : position === null || position > 10
            ? "Rank in top 10 on Google Maps"
            : undefined,
    },
    {
      label:
        rating !== null && rating >= 4.5
          ? `Rating ${rating}/5 (excellent)`
          : rating !== null && rating >= 4.0
            ? `Rating ${rating}/5 (good)`
            : `Rating ${rating ?? "N/A"}/5 (below 4.0)`,
      met: rating !== null && rating >= 4.0,
      points: rating !== null && rating >= 4.5 ? 30 : rating !== null && rating >= 4.0 ? 20 : 0,
      note:
        rating !== null && rating < 4.5
          ? rating >= 4.0
            ? "Reach 4.5+ to gain +10 more pts"
            : "Reach 4.0+ to gain +20 pts"
          : undefined,
    },
    {
      label:
        reviews !== null && reviews >= 100
          ? `${reviews.toLocaleString()} reviews (100+ ✓)`
          : reviews !== null && reviews >= 50
            ? `${reviews.toLocaleString()} reviews (50+)`
            : `${reviews ?? 0} reviews (need 50+)`,
      met: reviews !== null && reviews >= 50,
      points: reviews !== null && reviews >= 100 ? 20 : reviews !== null && reviews >= 50 ? 10 : 0,
      note:
        reviews !== null && reviews >= 50 && reviews < 100
          ? "Reach 100+ reviews for +10 more pts"
          : reviews === null || reviews < 50
            ? "Get 50+ reviews to gain +10 pts"
            : undefined,
    },
  ];

  const highlights: string[] = [];
  if (raw.title) highlights.push(raw.title);
  if (position !== null) highlights.push(`Position #${position}`);
  if (rating !== null) highlights.push(`★ ${rating}`);
  if (reviews !== null) highlights.push(`${reviews.toLocaleString()} reviews`);

  const tip =
    rating !== null && rating < 4.0
      ? "Encourage happy customers to leave reviews to boost your rating."
      : position !== null && position > 3
        ? "Add more photos, posts, and Q&A to your Google Business Profile to climb to top-3."
        : "Keep collecting reviews and responding promptly to maintain your ranking.";

  return { criteria, highlights, tip };
}

function getWebsiteCriteria(raw: WebsiteRaw): {
  criteria: Criterion[];
  highlights: string[];
  tip: string;
} {
  const contentLength = raw.content?.length ?? 0;
  const hasDescription = !!raw.description;
  const linksCount = raw.links?.length ?? 0;
  // null = could not check, false = checked and missing, true = found
  const schemaValue = raw.has_schema ?? (
    raw.content?.includes("LocalBusiness") || raw.content?.includes("schema.org") ? true : false
  );
  const schemaUnknown = raw.has_schema === null;
  const blogValue = raw.has_blog ?? (
    raw.links?.some((l: string) => l.toLowerCase().includes("blog")) || false
  );
  const blogUnknown = raw.has_blog === null;
  const hasTitle = !!raw.title;
  const scrapeError = !!raw.error;
  const contentQuality = raw.content_quality ?? null;

  // Content criterion — prefer AI quality assessment when available
  let contentCriterion: Criterion;
  if (scrapeError) {
    contentCriterion = {
      label: "Website content — could not verify (scrape failed)",
      met: false,
      unknown: true,
      points: 30,
    };
  } else if (contentQuality) {
    const q = contentQuality.quality;
    contentCriterion = {
      label:
        q === "high"
          ? `High quality content — ${contentQuality.summary ?? "all key info present"}`
          : q === "medium"
            ? `Decent content — ${contentQuality.summary ?? "some improvements possible"}`
            : `Low quality content — ${contentQuality.summary ?? "major content gaps"}`,
      met: q !== "low",
      points: 30,
    };
  } else {
    contentCriterion = {
      label:
        contentLength > 500
          ? `Content found (${contentLength.toLocaleString()} chars)`
          : `Very little content (${contentLength} chars — need 500+)`,
      met: contentLength > 500,
      points: 30,
    };
  }

  const criteria: Criterion[] = [
    contentCriterion,
    {
      label: hasDescription ? "Meta description present" : "No meta description found",
      met: hasDescription,
      points: 15,
    },
    {
      label:
        linksCount >= 3
          ? `${linksCount} internal/external links (3+ ✓)`
          : `${linksCount} link${linksCount !== 1 ? "s" : ""} found (need 3+)`,
      met: linksCount >= 3,
      points: 15,
    },
    {
      label: schemaUnknown
        ? "Schema markup — could not verify (check failed)"
        : schemaValue
          ? "LocalBusiness Schema markup found"
          : "No Schema markup found",
      met: schemaValue === true,
      unknown: schemaUnknown,
      points: 20,
    },
    {
      label: hasTitle ? "Page title present" : "No page title found",
      met: hasTitle,
      points: 10,
    },
    {
      label: blogUnknown
        ? "Blog — could not verify (check failed)"
        : blogValue
          ? "Blog link found"
          : "No blog link found",
      met: blogValue === true,
      unknown: blogUnknown,
      points: 10,
    },
  ];

  const highlights: string[] = [];
  if (raw.title) highlights.push(raw.title);
  if (contentLength > 0)
    highlights.push(`${contentLength.toLocaleString()} chars of content`);
  if (linksCount > 0) highlights.push(`${linksCount} links`);

  const tip = !hasSchema
    ? "Add LocalBusiness JSON-LD Schema markup to your homepage to unlock +20 pts."
    : !hasDescription
      ? "Write a concise meta description to improve click-through rate and score."
      : !hasBlogLink
        ? "A blog helps with Local Authority — add one to gain +10 pts here."
        : "Your website is in great shape! Keep content fresh and monitor Schema validity.";

  return { criteria, highlights, tip };
}

function getLocalAuthorityCriteria(raw: LocalAuthorityRaw): {
  criteria: Criterion[];
  highlights: string[];
  tip: string;
} {
  const mentionCount = raw.mention_count ?? 0;
  const onBestOfList = raw.on_best_of_list ?? false;

  const criteria: Criterion[] = [
    {
      label:
        mentionCount >= 5
          ? `${mentionCount} local mentions (5+ ✓)`
          : mentionCount >= 3
            ? `${mentionCount} local mentions (3–4)`
            : mentionCount >= 1
              ? `${mentionCount} local mention${mentionCount !== 1 ? "s" : ""}`
              : "No local mentions found",
      met: mentionCount >= 1,
      points:
        mentionCount >= 5 ? 80 : mentionCount >= 3 ? 60 : mentionCount >= 1 ? 40 : 10,
      note:
        mentionCount < 5
          ? mentionCount >= 3
            ? "Get 5+ mentions for maximum base score"
            : "Get 3+ mentions for +20 pts"
          : undefined,
    },
    {
      label: onBestOfList
        ? "Featured on a 'Best of' list"
        : "Not on any 'Best of' list",
      met: onBestOfList,
      points: 20,
    },
  ];

  const highlights: string[] = [];
  if (mentionCount > 0) highlights.push(`${mentionCount} local mentions`);
  if (onBestOfList) highlights.push("On Best-of list");
  if (raw.sources?.length) {
    raw.sources.slice(0, 2).forEach((s) => highlights.push(s.title));
  }

  const tip = !onBestOfList
    ? "Reach out to local bloggers and news sites to get featured on 'Best of' lists for +20 pts."
    : mentionCount < 5
      ? "Build more local citations on Yelp, TripAdvisor, and local directories."
      : "Strong local presence! Keep earning press coverage to maintain authority.";

  return { criteria, highlights, tip };
}

function getYouTubeCriteria(raw: YouTubeRaw): {
  criteria: Criterion[];
  highlights: string[];
  tip: string;
} {
  const videoCount = raw.video_count ?? 0;
  const hasOwnChannel = raw.has_own_channel ?? false;

  const criteria: Criterion[] = [
    {
      label:
        videoCount >= 5
          ? `${videoCount} videos found (5+ ✓)`
          : videoCount >= 2
            ? `${videoCount} videos found (2–4)`
            : videoCount >= 1
              ? `${videoCount} video found`
              : "No YouTube videos found",
      met: videoCount >= 1,
      points: videoCount >= 5 ? 70 : videoCount >= 2 ? 50 : videoCount >= 1 ? 30 : 10,
      note:
        videoCount < 5
          ? videoCount >= 2
            ? "Get 5+ videos for maximum base score"
            : "Get 2+ videos for +20 pts"
          : undefined,
    },
    {
      label: hasOwnChannel ? "Has own YouTube channel" : "No dedicated YouTube channel",
      met: hasOwnChannel,
      points: 20,
    },
  ];

  const highlights: string[] = [];
  if (videoCount > 0) highlights.push(`${videoCount} video${videoCount !== 1 ? "s" : ""}`);
  if (hasOwnChannel) highlights.push("Own channel");
  if (raw.videos?.length) {
    raw.videos.slice(0, 2).forEach((v) => highlights.push(`"${v.title}"`));
  }

  const tip = !hasOwnChannel
    ? "Create a YouTube channel to establish a branded presence and unlock +20 pts."
    : videoCount < 5
      ? "Post more videos — tutorials, testimonials, or behind-the-scenes — to reach 5+ for max score."
      : "Great YouTube presence! Add shorts and reply to comments to stay on top.";

  return { criteria, highlights, tip };
}

function getAIReadinessCriteria(raw: AIReadinessRaw): {
  criteria: Criterion[];
  highlights: string[];
  tip: string;
} {
  // null = could not check, false/true = checked result
  const schemaUnknown = raw.has_schema === null;
  const hasSchema = raw.has_schema ?? false;
  const reviewQuality = raw.review_quality ?? null;
  const reviewKeywords = raw.review_keywords ?? false;
  const napConsistent = raw.nap_consistent ?? false;
  const localMentions = raw.local_mentions ?? 0;

  // Build review keyword label based on AI quality assessment (Rule 7)
  let reviewLabel: string;
  let reviewMet: boolean;
  let reviewUnknown: boolean = false;
  if (reviewQuality === "high") {
    reviewLabel = "Reviews contain specific product/service keywords";
    reviewMet = true;
  } else if (reviewQuality === "medium") {
    reviewLabel = "Reviews have some product keywords — encourage more specific reviews";
    reviewMet = true;
  } else if (reviewQuality === "low") {
    reviewLabel = "Reviews lack specific keywords — ask customers to mention what they ordered";
    reviewMet = false;
  } else if (reviewKeywords) {
    reviewLabel = "50+ reviews (keyword analysis pending)";
    reviewMet = true;
  } else if (reviewQuality === null && !reviewKeywords) {
    reviewLabel = "Not enough reviews for keyword analysis";
    reviewMet = false;
    reviewUnknown = true;
  } else {
    reviewLabel = "Review keyword analysis unavailable";
    reviewMet = false;
    reviewUnknown = true;
  }

  const criteria: Criterion[] = [
    {
      label: schemaUnknown
        ? "Schema markup — could not verify (check failed)"
        : hasSchema
          ? "Schema markup present"
          : "No Schema markup found",
      met: hasSchema,
      unknown: schemaUnknown,
      points: 30,
    },
    {
      label: reviewLabel,
      met: reviewMet,
      unknown: reviewUnknown,
      points: 25,
    },
    {
      label: napConsistent
        ? "NAP (Name/Address/Phone) consistent"
        : "NAP inconsistency detected",
      met: napConsistent,
      points: 25,
    },
    {
      label:
        localMentions >= 3
          ? `${localMentions} local mentions (3+ ✓)`
          : `${localMentions} local mention${localMentions !== 1 ? "s" : ""} (need 3+)`,
      met: localMentions >= 3,
      points: 20,
    },
  ];

  const highlights: string[] = [];
  if (!schemaUnknown && hasSchema) highlights.push("Schema markup ✓");
  if (napConsistent) highlights.push("NAP consistent ✓");
  if (reviewQuality) highlights.push(`Review quality: ${reviewQuality}`);
  if (localMentions > 0) highlights.push(`${localMentions} local mentions`);

  const tip = schemaUnknown
    ? "Schema markup could not be checked — verify your site is accessible and run a new audit."
    : !hasSchema
      ? "Add LocalBusiness JSON-LD to your site — it's the single biggest AI readiness boost (+30 pts)."
      : !napConsistent
        ? "Ensure your business name, address, and phone match exactly across Google, Yelp, and your website."
        : reviewQuality === "low" || (!reviewQuality && !reviewKeywords)
          ? "Encourage customers to leave detailed reviews mentioning your services to improve keyword coverage."
          : "Excellent AI readiness! You're well-positioned for AI-powered search results.";

  return { criteria, highlights, tip };
}

export function getDimensionBreakdown(
  dimension: string,
  rawData: RawData,
): { criteria: Criterion[]; highlights: string[]; tip: string } {
  const raw = (rawData ?? {}) as Record<string, unknown>;

  switch (dimension) {
    case "google_maps":
      return getGoogleMapsCriteria(raw as GoogleMapsRaw);
    case "website":
      return getWebsiteCriteria(raw as WebsiteRaw);
    case "local_authority":
      return getLocalAuthorityCriteria(raw as LocalAuthorityRaw);
    case "youtube":
      return getYouTubeCriteria(raw as YouTubeRaw);
    case "ai_readiness":
      return getAIReadinessCriteria(raw as AIReadinessRaw);
    default:
      return { criteria: [], highlights: [], tip: "" };
  }
}

// ─── Labels ───────────────────────────────────────────────────────────────────

export const DIMENSION_LABELS: Record<string, string> = {
  google_maps: "Google Maps",
  website: "Website & SEO",
  local_authority: "Local Authority",
  youtube: "YouTube",
  ai_readiness: "AI Readiness",
};

// ─── Compact clickable card ───────────────────────────────────────────────────

interface DimensionCardProps {
  dimension: Dimension;
  selected?: boolean;
  onClick?: () => void;
}

export default function DimensionCard({
  dimension,
  selected = false,
  onClick,
}: DimensionCardProps) {
  const label = DIMENSION_LABELS[dimension.dimension] ?? dimension.dimension;
  const status = getStatusLabel(dimension.score);

  return (
    <button
      onClick={onClick}
      className={[
        "flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-200 text-center w-full cursor-pointer",
        "bg-surface-container-lowest shadow-ambient",
        selected
          ? "ring-2 ring-primary bg-primary/5 shadow-md"
          : "hover:bg-surface-container-low hover:shadow-md hover:scale-[1.02]",
      ].join(" ")}
      aria-pressed={selected}
    >
      {/* Score ring — compact 48px */}
      <ScoreRing score={dimension.score} size={52} strokeWidth={5} />

      {/* Name */}
      <span className="font-headline font-extrabold text-on-surface text-xs leading-tight">
        {label}
      </span>

      {/* Status */}
      <span className={`text-[10px] font-medium ${status.color}`}>
        {status.label}
      </span>

      {/* Click affordance */}
      {selected ? (
        <span className="material-symbols-outlined text-primary text-base leading-none">
          expand_less
        </span>
      ) : (
        <span className="flex items-center gap-0.5 text-[10px] font-medium text-on-surface-variant">
          Details
          <span className="material-symbols-outlined text-sm leading-none">
            chevron_right
          </span>
        </span>
      )}

      {/* Stale badge */}
      {dimension.is_stale && (
        <span className="text-[9px] text-yellow-600 bg-yellow-50 px-1.5 py-0.5 rounded">
          stale
        </span>
      )}
    </button>
  );
}
