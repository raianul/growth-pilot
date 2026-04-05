import { useEffect, useState } from "react";
import { GrowthPilotScore, CompetitorScorecard, SocialLinks, MenuHighlights, PricePositioning } from "./ResultSections";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/v1";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return (
    <span className={`material-symbols-outlined ${className}`}>{name}</span>
  );
}

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type PhaseStatus = "pending" | "running" | "done" | "error" | "rejected";

type Phase = {
  key: string;
  label: string;
  message: string;
  status: PhaseStatus;
};

type AuditResult = {
  business: {
    name: string;
    address: string;
    rating: number | null;
    review_count: number | null;
    place_id: string | null;
    category: string;
    types: string[];
    thumbnail?: string | null;
  };
  growthpilot_score?: {
    score: number;
    max: number;
    factors: { name: string; score: number; weight: number; detail: string }[];
  };
  competitor_scorecard?: {
    name: string;
    is_owner: boolean;
    rating: number | null;
    review_count: number;
    website: boolean;
    facebook: boolean;
    instagram: boolean;
    tiktok: boolean;
    foodpanda: boolean;
  }[] | null;
  online_presence: {
    google_maps: {
      status: string;
      rating: number | null;
      review_count: number | null;
    };
  };
  social_links?: {
    website: string | null;
    facebook: string | null;
    instagram: string | null;
    tiktok: string | null;
  };
  competitor_comparison: {
    area_business_count?: number;
    you?: { rating: number | null; review_count: number | null };
    area_average?: { rating: number | null; review_count: number | null };
    top_competitor?: {
      name: string;
      rating: number | null;
      review_count: number | null;
    };
  };
  review_analysis: {
    summary?: string;
    top_praised?: string[];
    top_complaints?: string[];
    sentiment?: string;
    improvement_suggestions?: string[];
  };
  top_gaps: {
    dimension: string;
    type: string;
    severity: string;
    message: string;
  }[];
  menu_highlights?: { title: string; price?: string }[] | null;
  price_details?: { distribution: { price: string; percentage: number }[]; total_reported?: number } | null;
  audit_meta?: {
    audited_at: string | null;
    expires_at: string | null;
  };
};

const PHASE_DEFS = [
  { key: "validation", label: "Validation", message: "Checking your business..." },
  { key: "scraping", label: "Google Maps", message: "Fetching your listing data..." },
  { key: "competitors", label: "Competitors", message: "Comparing with nearby businesses..." },
  { key: "website", label: "Website / SEO", message: "Analyzing your website..." },
  { key: "local_authority", label: "Local Presence", message: "Checking mentions and directories..." },
  { key: "ai_readiness", label: "AI Readiness", message: "Checking AI visibility..." },
  { key: "reviews", label: "Review Analysis", message: "Analyzing customer feedback..." },
  { key: "gaps", label: "Opportunities", message: "Finding your biggest gaps..." },
];

/* ------------------------------------------------------------------ */
/*  Audit Cache Info                                                   */
/* ------------------------------------------------------------------ */

function AuditCacheInfo({ auditedAt, expiresAt }: { auditedAt: string; expiresAt: string | null }) {
  const [showTip, setShowTip] = useState(false);

  const auditDate = new Date(auditedAt);
  const expiryDate = expiresAt ? new Date(expiresAt) : null;

  const formatDate = (d: Date) =>
    d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  return (
    <div className="mt-2 relative inline-block">
      <button
        onClick={() => setShowTip((v) => !v)}
        className="flex items-center gap-1.5 min-h-[44px] text-xs text-on-surface-variant/60 hover:text-on-surface-variant transition"
      >
        <Icon name="schedule" className="text-sm" />
        Audited {formatDate(auditDate)}
      </button>
      {showTip && (
        <div className="absolute left-0 top-full mt-1 z-50 rounded-lg bg-surface-container-lowest shadow-ambient p-3 w-72">
          <div className="text-xs text-on-surface-variant space-y-1.5">
            <div className="flex items-center gap-2">
              <Icon name="cached" className="text-sm text-on-surface-variant/50" />
              Serving cached results from {formatDate(auditDate)}
            </div>
            {expiryDate && (
              <div className="flex items-center gap-2">
                <Icon name="update" className="text-sm text-on-surface-variant/50" />
                Fresh audit available after {formatDate(expiryDate)}
              </div>
            )}
          </div>
          <button
            onClick={() => setShowTip(false)}
            className="mt-2 text-xs text-primary font-medium"
          >
            Got it
          </button>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Status Tracker — vertical checklist                                */
/* ------------------------------------------------------------------ */

function StatusTracker({ phases, auditMeta }: { phases: Phase[]; auditMeta?: { audited_at: string | null; expires_at: string | null } }) {
  const doneCount = phases.filter((p) => p.status === "done").length;
  const allDone = doneCount === phases.length;
  const hasRejected = phases.some((p) => p.status === "rejected");

  const headerText = allDone
    ? "Audit Complete"
    : hasRejected
    ? "Audit Stopped"
    : "Running Audit...";

  return (
    <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className={`font-headline text-base font-extrabold ${hasRejected ? "text-amber-700" : "text-on-surface"}`}>
            {headerText}
          </div>
          {allDone && auditMeta?.audited_at && (
            <AuditCacheInfo auditedAt={auditMeta.audited_at} expiresAt={auditMeta.expires_at} />
          )}
        </div>
        <div className="text-xs text-on-surface-variant mt-0.5">
          {doneCount}/{phases.length} steps
        </div>
      </div>

      {/* Checklist — 2 columns to stay compact */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        {phases.map((phase) => (
          <div key={phase.key} className="flex items-start gap-2">
            {/* Status icon */}
            {phase.status === "done" && (
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-green-100">
                <Icon name="check" className="text-green-600 text-sm" />
              </div>
            )}
            {phase.status === "running" && (
              <div className="flex h-6 w-6 shrink-0 items-center justify-center">
                <div className="h-5 w-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              </div>
            )}
            {phase.status === "pending" && (
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-container-high">
                <div className="h-1.5 w-1.5 rounded-full bg-on-surface-variant/30" />
              </div>
            )}
            {phase.status === "rejected" && (
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-100">
                <Icon name="do_not_disturb_on" className="text-amber-600 text-sm" />
              </div>
            )}
            {phase.status === "error" && (
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-100">
                <Icon name="close" className="text-red-500 text-sm" />
              </div>
            )}

            {/* Label + description */}
            <div>
              <div
                className={`text-sm ${
                  phase.status === "done"
                    ? "text-on-surface"
                    : phase.status === "running"
                    ? "text-primary font-semibold"
                    : phase.status === "rejected"
                    ? "text-amber-700"
                    : "text-on-surface-variant/50"
                }`}
              >
                {phase.label}
              </div>
              {(phase.status === "done" || phase.status === "running") && (
                <div className="text-xs text-on-surface-variant/60 mt-0.5">{phase.message}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Soft Gate (right column — appears after result)                    */
/* ------------------------------------------------------------------ */

function SoftGate({ auditId }: { auditId: string }) {
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");
  const [whatsapp, setWhatsapp] = useState("");

  async function handleCapture(e: React.FormEvent) {
    e.preventDefault();
    if (!whatsapp.trim()) return;
    setState("sending");
    try {
      await fetch(`${API_BASE}/audit/free/${auditId}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ whatsapp_number: whatsapp.trim() }),
      });
      setState("done");
    } catch {
      setState("idle");
    }
  }

  if (state === "done") {
    return (
      <div className="rounded-lg bg-gradient-to-br from-primary to-primary-container p-6 shadow-ambient text-center text-white">
        <Icon name="check_circle" className="text-4xl" />
        <div className="mt-3 font-headline text-base font-extrabold">
          Report sent to WhatsApp!
        </div>
        <p className="mt-1.5 text-sm text-white/80">
          Check your WhatsApp — your audit report is on the way.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-gradient-to-br from-primary to-primary-container p-5 shadow-ambient">
      <div className="font-headline text-base font-extrabold text-white leading-snug">
        Get this report on WhatsApp
      </div>
      <p className="mt-1.5 text-sm text-white/80">
        We'll send your full audit and improvement tips — free.
      </p>
      <form onSubmit={handleCapture} className="mt-4 space-y-3">
        <div>
          <input
            type="tel"
            required
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            placeholder="01XXXXXXXXX"
            inputMode="tel"
            className="w-full rounded-lg bg-white/95 px-4 py-3.5 text-sm text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-2 focus:ring-white/40"
          />
          <p className="mt-1.5 text-xs text-white/60">Your WhatsApp number (Bangladesh)</p>
        </div>
        <button
          type="submit"
          disabled={state === "sending"}
          className="w-full rounded-lg bg-white py-3.5 font-headline text-sm font-extrabold text-primary transition hover:bg-white/90 disabled:opacity-60"
        >
          {state === "sending" ? "Sending..." : "Send to WhatsApp"}
        </button>
      </form>
      <p className="mt-3 text-xs text-white/50 text-center">No spam. One-time report only.</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Result Cards (left column)                                         */
/* ------------------------------------------------------------------ */

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "green"
      ? "bg-green-100 text-green-700"
      : status === "yellow"
      ? "bg-amber-100 text-amber-700"
      : "bg-red-100 text-red-700";
  const label =
    status === "green" ? "Looking Good" : status === "yellow" ? "Could Be Better" : "Needs Attention";
  return <span className={`rounded-full px-3 py-1 text-xs font-bold ${color}`}>{label}</span>;
}

function ResultCards({ result }: { result: AuditResult }) {
  const gm = result.online_presence.google_maps as {
    status: string;
    rating: number | null;
    review_count: number | null;
    rating_vs_area?: string;
    reviews_vs_area?: string;
  };
  const website = (result.online_presence as Record<string, any>).website || {};
  const localAuth = (result.online_presence as Record<string, any>).local_authority || {};
  const aiReady = (result.online_presence as Record<string, any>).ai_readiness || {};
  const comp = result.competitor_comparison;
  const review = result.review_analysis;
  const gaps = result.top_gaps;

  // Color helpers for comparison
  const vsColor = (vs: string | undefined) =>
    vs === "ahead" ? "text-green-600" : vs === "behind" ? "text-red-500" : "text-on-surface";
  const vsIcon = (vs: string | undefined) =>
    vs === "ahead" ? "arrow_upward" : vs === "behind" ? "arrow_downward" : null;

  return (
    <div className="space-y-5">
      {/* 1. GrowthPilot Score */}
      {result.growthpilot_score && (
        <GrowthPilotScore score={result.growthpilot_score} />
      )}

      {/* 2. Competitor Scorecard */}
      {result.competitor_scorecard && result.competitor_scorecard.length > 1 && (
        <CompetitorScorecard scorecard={result.competitor_scorecard} />
      )}

      {/* 3. Competitor Comparison — the gut punch */}
      {comp.area_average && (
        <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
          <div className="font-headline font-extrabold text-on-surface mb-1">
            How you compare
          </div>
          <div className="text-xs text-on-surface-variant mb-4">
            {comp.area_business_count
              ? `Live data from Google Maps — vs ${comp.area_business_count} restaurants in your area`
              : "Live data from Google Maps"}
          </div>

          {/* Reviews row */}
          <div className="grid grid-cols-3 gap-4 text-center mb-4">
            <div>
              <div className="text-xs text-on-surface-variant mb-1">You</div>
              <div className={`font-headline font-extrabold text-2xl ${vsColor(gm.reviews_vs_area)}`}>
                {comp.you?.review_count?.toLocaleString() ?? "—"}
              </div>
              <div className="flex items-center justify-center gap-0.5 text-xs text-on-surface-variant">
                {vsIcon(gm.reviews_vs_area) && (
                  <Icon name={vsIcon(gm.reviews_vs_area)!} className={`text-sm ${vsColor(gm.reviews_vs_area)}`} />
                )}
                reviews
              </div>
            </div>
            <div>
              <div className="text-xs text-on-surface-variant mb-1">Area Avg</div>
              <div className="font-headline font-extrabold text-2xl text-on-surface-variant">
                {comp.area_average?.review_count?.toLocaleString() ?? "—"}
              </div>
              <div className="text-xs text-on-surface-variant">reviews</div>
            </div>
            <div>
              <div className="text-xs text-on-surface-variant mb-1">Top Rival</div>
              <div className="font-headline font-extrabold text-2xl text-on-surface-variant">
                {comp.top_competitor?.review_count?.toLocaleString() ?? "—"}
              </div>
              <div className="text-xs text-on-surface-variant">reviews</div>
            </div>
          </div>

          {/* Rating row */}
          <div className="grid grid-cols-3 gap-4 text-center pt-3 mt-1">
            <div>
              <div className={`font-headline font-extrabold text-lg ${vsColor(gm.rating_vs_area)}`}>
                {comp.you?.rating ?? "—"}★
                {vsIcon(gm.rating_vs_area) && (
                  <Icon name={vsIcon(gm.rating_vs_area)!} className={`text-sm inline ${vsColor(gm.rating_vs_area)}`} />
                )}
              </div>
              <div className="text-xs text-on-surface-variant">rating</div>
            </div>
            <div>
              <div className="font-headline font-extrabold text-lg text-on-surface-variant">
                {comp.area_average?.rating ?? "—"}★
              </div>
              <div className="text-xs text-on-surface-variant">rating</div>
            </div>
            <div>
              <div className="font-headline font-extrabold text-lg text-on-surface-variant">
                {comp.top_competitor?.rating ?? "—"}★
              </div>
              <div className="text-xs text-on-surface-variant">rating</div>
              {comp.top_competitor?.name && (
                <div className="mt-1 text-xs text-on-surface-variant truncate">
                  {comp.top_competitor.name}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Online Presence Cards */}
      <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
        <div className="font-headline font-extrabold text-on-surface mb-4">Online Presence</div>
        <div className="space-y-3">
          {/* Google Maps */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Icon name="location_on" className="text-primary text-lg" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm text-on-surface">Google Maps</div>
              <div className="text-xs text-on-surface-variant">
                {gm.rating ? `${gm.rating}★` : "No rating"} · {gm.review_count?.toLocaleString() ?? 0} reviews
              </div>
            </div>
            <StatusBadge status={gm.status} />
          </div>

          {/* Menu Link */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Icon name="restaurant_menu" className="text-primary text-lg" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm text-on-surface">Menu</div>
              <div className="text-xs text-on-surface-variant">
                {(gm as Record<string, unknown>).menu_link
                  ? <a href={(gm as Record<string, unknown>).menu_link as string} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{((gm as Record<string, unknown>).menu_link as string).replace(/^https?:\/\//, "").split("/")[0]}</a>
                  : "No menu link on Google Maps — add one to help customers decide"}
              </div>
            </div>
            <StatusBadge status={(gm as Record<string, unknown>).menu_link ? "green" : "red"} />
          </div>

          {/* Website */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Icon name="language" className="text-primary text-lg" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm text-on-surface">Website</div>
              <div className="text-xs text-on-surface-variant">
                {!website.has_website
                  ? "No website found — customers can't find you outside Google Maps"
                  : !website.has_content && website.url
                  ? `Listed on Google Maps but we couldn't scan it (${website.url.replace(/^https?:\/\//, "").split("/")[0]})`
                  : website.content_quality === "high"
                  ? "Strong website with good content"
                  : website.content_quality === "medium"
                  ? "Website found but content could be stronger"
                  : "Your website has very little content. Google can barely read it."}
              </div>
            </div>
            <StatusBadge status={website.status || "red"} />
          </div>

          {/* Local Presence */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Icon name="public" className="text-primary text-lg" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm text-on-surface">Local Presence</div>
              <div className="text-xs text-on-surface-variant">
                {(localAuth.mention_count ?? 0) === 0
                  ? "Not found on any review sites or local blogs"
                  : (localAuth.mention_count ?? 0) < 3
                  ? `Found on ${localAuth.mention_count} site${localAuth.mention_count !== 1 ? "s" : ""} — most competitors have more`
                  : `Found on ${localAuth.mention_count} sites${localAuth.on_best_of_list ? " including a best-of list" : ""}`}
              </div>
            </div>
            <StatusBadge status={localAuth.status || "red"} />
          </div>

          {/* AI Readiness */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Icon name="smart_toy" className="text-primary text-lg" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm text-on-surface">AI Search Visibility</div>
              <div className="text-xs text-on-surface-variant">
                {(aiReady.score ?? 0) >= 60
                  ? "AI tools like ChatGPT and Google AI can find and recommend you"
                  : (aiReady.score ?? 0) >= 30
                  ? "AI search tools can partially find you, but your website isn't helping"
                  : "AI assistants like ChatGPT can barely find your business online"}
              </div>
            </div>
            <StatusBadge status={aiReady.status || "red"} />
          </div>
        </div>
      </div>

      {/* 4. Social Links */}
      {result.social_links && (
        <SocialLinks links={result.social_links} />
      )}

      {/* 5. Delivery Platforms */}
      {localAuth.delivery_platforms && (
        <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
          <div className="font-headline font-extrabold text-on-surface mb-3">
            Delivery Platforms
          </div>
          <div className="space-y-2">
            {(localAuth.delivery_platforms.found as { title: string; url: string; domain: string; platform: string; rating?: number; reviews?: number }[] || []).map((p, i: number) => (
              <a
                key={`df${i}`}
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 rounded-lg p-3 -mx-1 hover:bg-surface-container-low transition"
              >
                <img
                  src={`https://www.google.com/s2/favicons?domain=${p.domain}&sz=32`}
                  alt=""
                  className="h-8 w-8 shrink-0 rounded"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-on-surface">{p.platform}</div>
                  <div className="text-xs text-on-surface-variant">
                    {p.rating && <span>{p.rating}★</span>}
                    {p.reviews && <span> · {p.reviews.toLocaleString()} reviews</span>}
                    {!p.rating && !p.reviews && <span>{p.domain}</span>}
                  </div>
                </div>
                <Icon name="open_in_new" className="text-on-surface-variant/40 text-base shrink-0" />
              </a>
            ))}
            {(localAuth.delivery_platforms.missing as string[] || []).map((name: string, i: number) => (
              <div
                key={`dm${i}`}
                className="flex items-center gap-3 rounded-lg p-3 -mx-1"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100">
                  <Icon name="close" className="text-red-500 text-base" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-on-surface">{name}</div>
                  <div className="text-xs text-on-surface-variant">Not found — customers can't order from you here</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Online Mentions — review sites + other */}
      {(() => {
        const reviewSites = (localAuth.review_sites || []) as { title: string; url: string; domain: string; platform: string; rating?: number; reviews?: number }[];
        const otherMentions = (localAuth.other_mentions || []) as { title: string; url: string; domain: string; rating?: number; reviews?: number }[];
        const allMentions = [...reviewSites, ...otherMentions]
          .filter((s) => {
            const bizName = (result.business.name || "").toLowerCase().replace(/[^a-z0-9]/g, "");
            const domainClean = s.domain.toLowerCase().replace("www.", "").split(".")[0].replace(/[^a-z0-9]/g, "");
            return !(domainClean === bizName || s.domain.toLowerCase().includes(bizName));
          })
          .slice(0, 3);

        if (allMentions.length === 0) return null;

        return (
          <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
            <div className="font-headline font-extrabold text-on-surface mb-3">
              Where people find you online
            </div>
            <div className="space-y-2.5">
              {allMentions.map((source, i) => (
                <a
                  key={i}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-3 rounded-lg p-3 -mx-1 hover:bg-surface-container-low transition"
                >
                  <img
                    src={`https://www.google.com/s2/favicons?domain=${source.domain}&sz=32`}
                    alt=""
                    className="h-5 w-5 mt-0.5 shrink-0 rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-on-surface truncate">
                      {source.title}
                    </div>
                    <div className="text-xs text-on-surface-variant mt-0.5">
                      {source.domain}
                      {source.rating && <span> · {source.rating}★</span>}
                      {source.reviews && <span> ({source.reviews.toLocaleString()})</span>}
                    </div>
                  </div>
                  <Icon name="open_in_new" className="text-on-surface-variant/40 text-base shrink-0 mt-0.5" />
                </a>
              ))}
            </div>
          </div>
        );
      })()}

      {/* 7. Menu Highlights */}
      {result.menu_highlights && result.menu_highlights.length > 0 && (
        <MenuHighlights items={result.menu_highlights} />
      )}

      {/* 8. Price Positioning */}
      {result.price_details && result.price_details.distribution && (
        <PricePositioning data={result.price_details} />
      )}

      {/* 9-10. Reviews + Gaps */}
      {gaps.length > 0 && (
        <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
          <div className="font-headline font-extrabold text-on-surface mb-3">
            Your biggest opportunities
          </div>
          <div className="space-y-3">
            {gaps.map((gap, i) => (
              <div key={i} className="flex items-start gap-3">
                <Icon
                  name={
                    gap.severity === "high"
                      ? "priority_high"
                      : gap.severity === "medium"
                      ? "warning"
                      : "info"
                  }
                  className={`text-lg mt-0.5 ${
                    gap.severity === "high"
                      ? "text-red-500"
                      : gap.severity === "medium"
                      ? "text-amber-500"
                      : "text-primary"
                  }`}
                />
                <p className="text-sm text-on-surface leading-relaxed">{gap.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review Analysis — two columns + separate suggestions */}
      {review.top_praised && review.top_praised.length > 0 && (
        <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
          <div className="font-headline font-extrabold text-on-surface mb-2">
            What your customers say
          </div>
          {review.summary && (
            <p className="text-sm text-on-surface-variant mb-4">{review.summary}</p>
          )}

          {/* Two columns: praised and complaints */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Customers love */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Icon name="thumb_up" className="text-green-600 text-base" />
                <span className="text-sm font-semibold text-green-700">Customers love</span>
              </div>
              <div className="space-y-2">
                {review.top_praised?.slice(0, 4).map((item, i) => (
                  <div key={`p${i}`} className="flex items-start gap-2">
                    <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-green-400" />
                    <span className="text-sm text-on-surface">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Could improve */}
            {review.top_complaints && review.top_complaints.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <Icon name="thumb_down" className="text-red-500 text-base" />
                  <span className="text-sm font-semibold text-red-600">Could improve</span>
                </div>
                <div className="space-y-2">
                  {review.top_complaints?.slice(0, 4).map((item, i) => (
                    <div key={`c${i}`} className="flex items-start gap-2">
                      <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />
                      <span className="text-sm text-on-surface">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Suggestions — separate section */}
          {review.improvement_suggestions && review.improvement_suggestions.length > 0 && (
            <div className="mt-6">
              <div className="flex items-center gap-1.5 mb-2">
                <Icon name="lightbulb" className="text-amber-500 text-base" />
                <span className="text-sm font-semibold text-amber-700">Suggestions</span>
              </div>
              <div className="space-y-2">
                {review.improvement_suggestions.slice(0, 3).map((item, i) => (
                  <div key={`s${i}`} className="flex items-start gap-2">
                    <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                    <span className="text-sm text-on-surface">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Audit Page                                                         */
/* ------------------------------------------------------------------ */

type AuditRoute =
  | { type: "url"; mapsUrl: string }
  | { type: "place_id"; placeId: string; businessName: string }
  | { type: "slug"; slug: string; renew?: boolean };

export default function AuditPage({
  audit,
  onBack,
}: {
  audit: AuditRoute;
  onBack: () => void;
}) {
  const [phases, setPhases] = useState<Phase[]>(
    PHASE_DEFS.map((d) => ({ ...d, status: "pending" }))
  );
  const [auditId, setAuditId] = useState<string | null>(null);
  const [businessName, setBusinessName] = useState(audit.type === "place_id" ? audit.businessName : "");
  const [notFound, setNotFound] = useState(false);
  const [address, setAddress] = useState("");
  const [result, setResult] = useState<AuditResult | null>(null);
  const [failed, setFailed] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const allDone = phases.every((p) => p.status === "done");
  const rejected = phases.some((p) => p.status === "rejected");
  const loading = !allDone && !failed && !rejected && !result;

  function updatePhases(progress: Record<string, string>, currentPhase: string | null) {
    setPhases((prev) =>
      prev.map((p) => {
        const serverStatus = progress[p.key];
        if (serverStatus === "done") return { ...p, status: "done" };
        if (serverStatus === "running") return { ...p, status: "running" };
        if (serverStatus === "rejected") return { ...p, status: "rejected" };
        if (serverStatus === "error") return { ...p, status: "error" };
        if (currentPhase === p.key && !serverStatus) return { ...p, status: "running" };
        return p;
      })
    );
  }

  function handleRejected(error: string | null) {
    setValidationError(error || "This business type is not supported.");
    setPhases((prev) =>
      prev.map((p) =>
        p.key === "validation" ? { ...p, status: "rejected" } : p
      )
    );
  }

  async function fetchResult(id: string) {
    try {
      const res = await fetch(`${API_BASE}/audit/free/${id}`);
      const data = await res.json();
      if (data.status === "completed" && data.result) {
        setPhases((prev) => prev.map((p) => ({ ...p, status: "done" })));
        setResult(data.result);
      } else if (data.status === "rejected") {
        handleRejected(data.validation_error);
      } else if (data.status === "failed") {
        setFailed(true);
      } else {
        setTimeout(() => fetchResult(id), 3000);
      }
    } catch {
      setFailed(true);
    }
  }

  function connectSSE(id: string) {
    const es = new EventSource(`${API_BASE}/audit/free/${id}/stream`);

    es.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data);
      updatePhases(data.phase_progress || {}, data.current_phase);
    });

    es.addEventListener("complete", (e) => {
      const data = JSON.parse(e.data);
      es.close();
      if (data.status === "rejected") {
        handleRejected(data.validation_error);
      } else if (data.status === "completed" && data.data) {
        setPhases((prev) => prev.map((p) => ({ ...p, status: "done" })));
        setResult(data.data);
      } else {
        fetchResult(id);
      }
    });

    es.onerror = () => {
      es.close();
      fetchResult(id);
    };

    return es;
  }

  useEffect(() => {
    let es: EventSource | null = null;

    (async () => {
      // For slug type: first look up the business, then decide to show cached or run new
      if (audit.type === "slug") {
        try {
          const lookupRes = await fetch(`${API_BASE}/businesses/${audit.slug}`);
          if (!lookupRes.ok) {
            setNotFound(true);
            return;
          }
          const lookupData = await lookupRes.json();
          setBusinessName(lookupData.business.business_name);
          setAddress(lookupData.business.address || "");

          // If cached audit exists and no renew requested, show it directly
          if (lookupData.has_audit && lookupData.audit_id && !audit.renew) {
            setAuditId(lookupData.audit_id);
            setPhases((prev) => prev.map((p) => ({ ...p, status: "done" })));
            fetchResult(lookupData.audit_id);
            return;
          }

          // Otherwise start a new audit using place_id
          setPhases((prev) =>
            prev.map((p) => (p.key === "validation" ? { ...p, status: "running" } : p))
          );
          const auditRes = await fetch(`${API_BASE}/audit/free`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ google_place_id: lookupData.business.google_place_id, renew: audit.renew || false }),
          });
          const auditData = await auditRes.json();
          if (!auditRes.ok) {
            handleRejected(auditData.detail || "Something went wrong.");
            return;
          }
          setAuditId(auditData.audit_id);
          if (auditData.business_name) setBusinessName(auditData.business_name);
          if (auditData.address) setAddress(auditData.address);
          setPhases((prev) =>
            prev.map((p) => (p.key === "validation" ? { ...p, status: "done" } : p))
          );
          if (auditData.status === "completed") {
            fetchResult(auditData.audit_id);
          } else {
            es = connectSSE(auditData.audit_id);
          }
        } catch {
          setNotFound(true);
        }
        return;
      }

      // For place_id and url types: existing flow
      setPhases((prev) =>
        prev.map((p) => (p.key === "validation" ? { ...p, status: "running" } : p))
      );

      const body = audit.type === "place_id"
        ? { google_place_id: audit.placeId }
        : { google_maps_url: audit.mapsUrl };

      try {
        const res = await fetch(`${API_BASE}/audit/free`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await res.json();

        if (!res.ok) {
          handleRejected(data.detail || "Something went wrong. Please try again.");
          return;
        }

        setAuditId(data.audit_id);
        if (data.business_name) setBusinessName(data.business_name);
        if (data.address) setAddress(data.address);

        // Update URL to slug if available
        if (data.business_name && audit.type === "place_id") {
          // Will be handled by the slug lookup next time
        }

        setPhases((prev) =>
          prev.map((p) => (p.key === "validation" ? { ...p, status: "done" } : p))
        );
        if (data.status === "completed") {
          fetchResult(data.audit_id);
        } else {
          es = connectSSE(data.audit_id);
        }
      } catch {
        handleRejected("Could not connect. Please try again.");
      }
    })();

    return () => { es?.close(); };
  }, [audit.type === "slug" ? (audit as any).slug : audit.type === "place_id" ? (audit as any).placeId : (audit as any).mapsUrl]);

  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary to-primary-container px-4 py-3">
        <div className="mx-auto max-w-6xl flex items-center gap-2">
          <button
            onClick={onBack}
            aria-label="Back to home"
            className="flex items-center gap-1.5 min-h-[44px] min-w-[44px] px-2 text-white/80 hover:text-white transition text-sm rounded-lg"
          >
            <Icon name="arrow_back" className="text-xl" />
            <span className="hidden sm:inline">Back</span>
          </button>
          <div className="flex-1 text-center">
            <span className="font-headline font-extrabold text-white">GrowthPilot</span>
          </div>
          {/* balanced spacer matching back button */}
          <div className="min-w-[44px] px-2" />
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-6xl px-6 py-6 space-y-6">
        {/* 404 — not found */}
        {notFound && (
          <div className="flex flex-col items-center justify-center py-24">
            <Icon name="search_off" className="text-6xl text-on-surface-variant/30" />
            <h1 className="mt-4 font-headline text-2xl font-extrabold text-on-surface">Restaurant not found</h1>
            <p className="mt-2 text-sm text-on-surface-variant">We couldn't find this business in our directory.</p>
            <button
              onClick={onBack}
              className="mt-6 rounded-lg bg-primary px-6 py-3 font-headline font-extrabold text-white transition hover:bg-primary-container"
            >
              Go to Homepage
            </button>
          </div>
        )}

        {/* Business name + address + cache info */}
        <div className="space-y-6" style={notFound ? {display: "none"} : undefined}>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/10 mt-1">
            <Icon name="restaurant" className="text-primary text-xl" />
          </div>
          <div>
          <h1 className="font-headline text-2xl font-extrabold text-on-surface">
            {result?.business.name || businessName || "Analyzing your business..."}
          </h1>
          {(result?.business.address || address) && (
            <p className="mt-1 text-sm text-on-surface-variant">
              {result?.business.address || address}
            </p>
          )}
        </div>
        </div>

        {/* Status tracker — full width while running */}
        {!allDone && !result && (
          <StatusTracker phases={phases} />
        )}

        {/* Loading placeholder — shows while we wait for the first result */}
        {loading && (
          <div className="rounded-lg bg-surface-container-lowest p-6 shadow-ambient text-center">
            <p className="text-sm text-on-surface-variant">
              Hang tight — this takes about 60 seconds.
            </p>
          </div>
        )}

        {/* Error state */}
        {failed && (
          <div className="rounded-lg bg-red-50 p-5 text-center">
            <Icon name="error" className="text-red-500 text-3xl" />
            <p className="mt-2 text-sm text-red-700">
              Something went wrong. Please go back and try again.
            </p>
          </div>
        )}

        {/* 2/3 + 1/3 layout — shows for results, validation errors, or completed audit */}
        {(result || validationError || allDone || rejected) && (
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="lg:w-2/3 space-y-5">
              {/* Validation feedback */}
              {validationError && (
                <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
                  <div className="font-headline font-extrabold text-on-surface mb-3">
                    Validation
                  </div>
                  <div className="flex items-start gap-3 rounded-lg bg-amber-50 p-4">
                    <Icon name="do_not_disturb_on" className="text-amber-600 text-xl mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm text-on-surface">{validationError}</p>
                      <button
                        onClick={onBack}
                        className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-container"
                      >
                        Try a different business
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Result cards */}
              {result && <ResultCards result={result} />}
            </div>

            <div className="lg:w-1/3 space-y-5">
              {/* Audit Complete moves here when done */}
              {(allDone || rejected) && (
                <StatusTracker phases={phases} auditMeta={result?.audit_meta} />
              )}
              <div className="lg:sticky lg:top-6">
                <SoftGate auditId={auditId || ""} />
              </div>
            </div>
          </div>
        )}
      </div>
      </div>

      {/* Footer */}
      <footer className="bg-surface-container-high px-6 py-8 mt-12">
        <div className="mx-auto max-w-6xl text-center">
          <div className="font-headline font-extrabold text-on-surface">GrowthPilot</div>
          <p className="mt-1 text-sm text-on-surface-variant">
            We make restaurants easier to find online.
          </p>
        </div>
      </footer>
    </div>
  );
}

