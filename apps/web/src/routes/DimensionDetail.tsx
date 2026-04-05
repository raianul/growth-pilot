import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { useUIStore } from "../store/uiStore";
import ContentDraft from "../components/ContentDraft";
import {
  getDimensionBreakdown,
  DIMENSION_LABELS,
  getStatusLabel,
} from "../components/DimensionCard";

interface Outlet {
  id: string;
}

interface Dimension {
  dimension: string;
  score: number;
  weight: number;
  is_stale: boolean;
  raw_data?: Record<string, unknown> | null;
}

interface Mission {
  id: string;
  title: string;
  description: string;
  channel: string;
  difficulty: "easy" | "medium" | "hard";
  estimated_minutes: number;
  impact_score: number;
  status: string;
}

interface ContentItem {
  id: string;
  channel: string;
  title: string;
  body: string;
  metadata: Record<string, unknown> | null;
  copy_count: number;
}

interface Audit {
  id: string;
  status: string;
  dimensions: Dimension[];
}

interface DashboardData {
  outlet_id: string;
  outlet_name: string;
  organization_name: string;
  latest_audit: Audit | null;
  active_missions: Mission[];
  next_audit_at: string | null;
}

const CHANNEL_DIMENSION: Record<string, string> = {
  google_maps: "google_maps",
  website: "website",
  social: "local_authority",
  youtube: "youtube",
  reddit: "local_authority",
  local_authority: "local_authority",
};

const DIFFICULTY_STYLES: Record<string, { bg: string; text: string }> = {
  easy: { bg: "bg-green-100", text: "text-green-700" },
  medium: { bg: "bg-yellow-100", text: "text-yellow-700" },
  hard: { bg: "bg-red-100", text: "text-red-600" },
};

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function VideoCard({ video, muted }: { video: { video_id: string; title: string; channel: string; views?: number; likes?: number; channel_subscribers?: number }; muted?: boolean }) {
  return (
    <a
      href={`https://youtube.com/watch?v=${video.video_id}`}
      target="_blank"
      rel="noopener noreferrer"
      className={`flex items-start gap-3 rounded-xl p-3 hover:bg-surface-container-low transition-colors group ${muted ? "opacity-80" : ""}`}
    >
      <span className={`material-symbols-outlined text-base mt-0.5 shrink-0 ${muted ? "text-on-surface-variant" : "text-red-500"}`}>
        smart_display
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors line-clamp-1">
          {video.title}
        </p>
        <div className="flex items-center gap-3 mt-1 text-[10px] text-on-surface-variant">
          {video.channel && (
            <span>{video.channel}</span>
          )}
          {(video.views ?? 0) > 0 && (
            <span className="flex items-center gap-0.5">
              <span className="material-symbols-outlined text-[10px]">visibility</span>
              {formatCount(video.views!)}
            </span>
          )}
          {(video.channel_subscribers ?? 0) > 0 && (
            <span className="flex items-center gap-0.5">
              <span className="material-symbols-outlined text-[10px]">group</span>
              {formatCount(video.channel_subscribers!)} subs
            </span>
          )}
        </div>
      </div>
    </a>
  );
}

export default function DimensionDetail() {
  const { key } = useParams<{ key: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedOutletId } = useUIStore();
  const [selectedMission, setSelectedMission] = useState<Mission | null>(null);

  const { data: outlets } = useQuery({
    queryKey: ["outlets"],
    queryFn: () => apiFetch<Outlet[]>("/outlets"),
  });
  const outletId = selectedOutletId ?? outlets?.[0]?.id;

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["dashboard", outletId],
    queryFn: () => apiFetch<DashboardData>(`/outlets/${outletId}/dashboard`),
    enabled: !!outletId,
  });

  // Fetch content for selected mission
  const { data: missionContent } = useQuery({
    queryKey: ["mission-content", selectedMission?.id],
    queryFn: () =>
      apiFetch<ContentItem[]>(`/missions/${selectedMission!.id}/content`),
    enabled: !!selectedMission,
  });

  const { mutate: markDone, isPending } = useMutation({
    mutationFn: () =>
      apiFetch(`/missions/${selectedMission!.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "completed" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setSelectedMission(null);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const dimension = dashboard?.latest_audit?.dimensions?.find(
    (d) => d.dimension === key,
  );
  const label = key ? (DIMENSION_LABELS[key] ?? key) : "";

  if (!dimension) {
    return (
      <div className="text-center py-16 text-on-surface-variant">
        No data for {label} yet. Run an audit first.
      </div>
    );
  }

  const status = getStatusLabel(dimension.score);
  const { criteria, tip } = getDimensionBreakdown(
    dimension.dimension,
    dimension.raw_data,
  );

  const missions = (dashboard?.active_missions ?? []).filter(
    (m) => CHANNEL_DIMENSION[m.channel] === key,
  );

  const sources = (dimension.raw_data?.sources ?? []) as {
    title: string;
    url: string;
    snippet: string;
    date?: string;
    domain?: string;
  }[];

  const videos = (dimension.raw_data?.videos ?? []) as {
    title: string;
    video_id: string;
    channel: string;
    confirmed?: boolean;
    views?: number;
    likes?: number;
    channel_subscribers?: number;
  }[];
  const confirmedVideos = videos.filter((v) => v.confirmed);
  const possibleVideos = videos.filter((v) => !v.confirmed);

  const gmData = dimension.raw_data as Record<string, unknown> | null;
  const reviewAnalysis = (gmData?.review_analysis ?? {}) as Record<string, unknown>;
  const recentReviews = (gmData?.recent_reviews ?? []) as any[];

  // Generate quick actions from failing criteria
  const CRITERIA_ACTIONS: Record<string, { title: string; description: string }> = {
    // Google Maps
    "Rating": { title: "Improve your Google rating", description: "Respond to negative reviews and encourage happy customers to leave 5-star reviews." },
    "review": { title: "Get more Google reviews", description: "Ask satisfied customers to leave a review. Place a QR code at your counter linking to your Google Maps page." },
    "position": { title: "Improve Maps ranking", description: "Complete your Google Business Profile — add photos, business hours, menu, and services." },
    // Website
    "Schema": { title: "Add Schema markup to your website", description: "Add LocalBusiness JSON-LD markup to your homepage. Send this to your web developer — it takes 10 minutes." },
    "blog": { title: "Start a blog on your website", description: "Add a blog section and post once a month about your specialty. This signals freshness to search engines and AI." },
    "links": { title: "Add internal links to your website", description: "Make sure your homepage links to About, Menu/Services, Contact, and other key pages." },
    "description": { title: "Add a meta description", description: "Add a meta description tag to your homepage — this is the snippet shown in Google search results." },
    // YouTube
    "channel": { title: "Create a YouTube channel", description: "Set up a branded YouTube channel for your business. Upload at least one video — a 60-second tour works great." },
    "video": { title: "Create video content", description: "Record a short video about your business — a tour, a behind-the-scenes, or a customer testimonial." },
    // AI Readiness
    "keyword": { title: "Encourage keyword-rich reviews", description: "Ask customers to mention specific products or services in their reviews (e.g., 'best döner' not just 'great food')." },
    "NAP": { title: "Fix NAP consistency", description: "Make sure your business Name, Address, and Phone match exactly across Google Maps, your website, and all directories." },
    "mention": { title: "Get listed on local directories", description: "Submit your business to Yelp, TripAdvisor, and local city guides to increase mentions." },
  };

  const failingCriteria = criteria
    .filter((c) => !c.met)
    .map((c) => {
      // Find matching action by checking if any key appears in the criteria label
      const matchKey = Object.keys(CRITERIA_ACTIONS).find((k) =>
        c.label.toLowerCase().includes(k.toLowerCase()),
      );
      if (!matchKey) return null;
      return CRITERIA_ACTIONS[matchKey];
    })
    .filter((a): a is { title: string; description: string } => a !== null);

  return (
    <div className="space-y-6">
      {/* Back */}
      <button
        onClick={() => navigate("/dashboard")}
        className="flex items-center gap-1.5 text-on-surface-variant hover:text-on-surface transition-colors text-sm font-medium"
      >
        <span className="material-symbols-outlined text-lg">arrow_back</span>
        Back to Dashboard
      </button>

      {/* Hero — full width across both columns */}
      <div className="bg-gradient-to-br from-primary to-primary-container rounded-xl p-6 text-white">
        <h1 className="font-headline font-extrabold text-2xl">{label}</h1>
        <p className="text-white/70 mt-1">{status.label}</p>
      </div>

      {/* Stale data banner (Rule 6) */}
      {dimension.is_stale && (
        <div className="flex items-center gap-2 bg-yellow-50 rounded-xl p-3">
          <span className="material-symbols-outlined text-yellow-600">schedule</span>
          <p className="text-sm text-yellow-700">
            This data is from a previous check and may be outdated. Run a new audit for fresh results.
          </p>
        </div>
      )}

      {/* Two-column layout below hero */}
      <div className="flex gap-6">
        {/* ─── Left column: Score + Data ─── */}
        <div className="flex-1 space-y-6 min-w-0">

        {/* What's working / What needs attention */}
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient space-y-5">
          {criteria.filter((c) => c.met).length > 0 && (
            <div>
              <h2 className="font-headline font-extrabold text-on-surface text-lg mb-3">
                What's working
              </h2>
              <ul className="space-y-2">
                {criteria
                  .filter((c) => c.met)
                  .map((c, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span
                        className="material-symbols-outlined text-base mt-0.5 shrink-0 text-green-600"
                        style={{ fontVariationSettings: "'FILL' 1" }}
                      >
                        check_circle
                      </span>
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-on-surface">{c.label}</span>
                        {c.note && (
                          <p className="text-xs text-on-surface-variant mt-0.5">
                            {c.note}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
              </ul>
            </div>
          )}

          {criteria.filter((c) => !c.met).length > 0 && (
            <div>
              <h2 className="font-headline font-extrabold text-on-surface text-lg mb-3">
                What needs attention
              </h2>
              <ul className="space-y-2">
                {criteria
                  .filter((c) => !c.met)
                  .map((c, i) => (
                    <li key={i} className="flex items-start gap-2">
                      {c.unknown ? (
                        <span className="material-symbols-outlined text-base mt-0.5 shrink-0 text-on-surface-variant">
                          help
                        </span>
                      ) : (
                        <span
                          className="material-symbols-outlined text-base mt-0.5 shrink-0 text-red-500"
                          style={{ fontVariationSettings: "'FILL' 1" }}
                        >
                          cancel
                        </span>
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-on-surface">{c.label}</span>
                        {c.note && (
                          <p className="text-xs text-on-surface-variant mt-0.5">
                            {c.note}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
              </ul>
            </div>
          )}

          {tip && (
            <div className="flex items-start gap-2 bg-primary/5 rounded-xl p-3">
              <span className="material-symbols-outlined text-primary text-base mt-0.5 shrink-0">
                lightbulb
              </span>
              <p className="text-xs text-on-surface-variant">
                <span className="font-semibold text-on-surface">Tip: </span>
                {tip}
              </p>
            </div>
          )}
        </div>

        {/* Google Maps profile */}
        {key === "google_maps" && gmData && (
          <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
            <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
              Your Google Maps Profile
            </h2>
            <div className="grid grid-cols-3 gap-4">
              {gmData.position != null && (
                <div className="text-center">
                  <p className="font-headline font-extrabold text-2xl text-on-surface">
                    #{String(gmData.position)}
                  </p>
                  <p className="text-xs text-on-surface-variant mt-1">
                    Maps Position
                  </p>
                </div>
              )}
              {gmData.rating != null && (
                <div className="text-center">
                  <p className="font-headline font-extrabold text-2xl text-on-surface">
                    {String(gmData.rating)}
                    <span className="text-yellow-500 text-lg">★</span>
                  </p>
                  <p className="text-xs text-on-surface-variant mt-1">
                    Rating
                  </p>
                </div>
              )}
              {gmData.reviews != null && (
                <div className="text-center">
                  <p className="font-headline font-extrabold text-2xl text-on-surface">
                    {Number(gmData.reviews).toLocaleString()}
                  </p>
                  <p className="text-xs text-on-surface-variant mt-1">
                    Reviews
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Review Analysis */}
        {key === "google_maps" && gmData?.review_analysis && (
          <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
            <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
              What your customers say
            </h2>

            {/* Summary */}
            {reviewAnalysis.summary && typeof reviewAnalysis.summary === "string" && (
              <p className="text-sm text-on-surface-variant mb-4">{reviewAnalysis.summary}</p>
            )}

            {/* Two columns: Praised vs Complaints */}
            <div className="grid grid-cols-2 gap-4">
              {/* Top praised */}
              <div>
                <h3 className="text-sm font-semibold text-green-700 flex items-center gap-1 mb-2">
                  <span className="material-symbols-outlined text-base" style={{fontVariationSettings: "'FILL' 1"}}>thumb_up</span>
                  Customers love
                </h3>
                <ul className="space-y-1.5">
                  {((reviewAnalysis.top_praised ?? []) as string[]).map((item, i) => (
                    <li key={i} className="text-xs text-on-surface-variant flex items-start gap-1.5">
                      <span className="text-green-500 mt-0.5">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Complaints */}
              <div>
                <h3 className="text-sm font-semibold text-red-600 flex items-center gap-1 mb-2">
                  <span className="material-symbols-outlined text-base" style={{fontVariationSettings: "'FILL' 1"}}>thumb_down</span>
                  Could improve
                </h3>
                <ul className="space-y-1.5">
                  {((reviewAnalysis.top_complaints ?? []) as string[]).map((item, i) => (
                    <li key={i} className="text-xs text-on-surface-variant flex items-start gap-1.5">
                      <span className="text-red-400 mt-0.5">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Improvement suggestions */}
            {((reviewAnalysis.improvement_suggestions ?? []) as string[]).length > 0 && (
              <div className="mt-4 pt-4 border-t border-outline-variant/10">
                <h3 className="text-sm font-semibold text-on-surface flex items-center gap-1 mb-2">
                  <span className="material-symbols-outlined text-primary text-base">lightbulb</span>
                  Suggestions from review analysis
                </h3>
                <ul className="space-y-1.5">
                  {((reviewAnalysis.improvement_suggestions ?? []) as string[]).map((s, i) => (
                    <li key={i} className="text-xs text-on-surface-variant flex items-start gap-1.5">
                      <span className="text-primary mt-0.5">→</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recent reviews sample */}
            {recentReviews.length > 0 && (
              <div className="mt-4 pt-4 border-t border-outline-variant/10">
                <h3 className="text-sm font-semibold text-on-surface mb-3">Recent reviews</h3>
                <div className="space-y-3">
                  {recentReviews.slice(0, 3).map((review, i) => (
                    <div key={i} className="bg-surface-container-low rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-yellow-500 text-xs">
                          {"★".repeat(review.rating || 0)}{"☆".repeat(5 - (review.rating || 0))}
                        </span>
                        {review.author && <span className="text-[10px] text-on-surface-variant">{review.author}</span>}
                        {review.date && <span className="text-[10px] text-on-surface-variant/60">{review.date}</span>}
                      </div>
                      <p className="text-xs text-on-surface-variant line-clamp-3">{review.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Where you're mentioned */}
        {sources.length > 0 && (
          <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
            <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
              Where you're mentioned
            </h2>
            <div className="space-y-2">
              {sources.map((source, i) => {
                const domain = source.domain || (() => {
                  try { return new URL(source.url).hostname; } catch { return ""; }
                })();
                return (
                  <a
                    key={i}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-3 rounded-xl p-3 hover:bg-surface-container-low transition-colors group"
                  >
                    {/* Site favicon */}
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${domain}&sz=32`}
                      alt=""
                      className="w-6 h-6 rounded mt-0.5 shrink-0"
                      loading="lazy"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors line-clamp-1">
                        {source.title}
                      </p>
                      {source.snippet && (
                        <p className="text-xs text-on-surface-variant mt-0.5 line-clamp-2">
                          {source.snippet}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-on-surface-variant/60">
                          {domain}
                        </span>
                        {source.date && (
                          <>
                            <span className="text-[10px] text-on-surface-variant/40">·</span>
                            <span className="text-[10px] text-on-surface-variant/60">
                              {source.date}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </a>
                );
              })}
            </div>
          </div>
        )}

        {/* YouTube videos — confirmed mentions */}
        {confirmedVideos.length > 0 && (
          <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
            <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
              Videos that mention your business
            </h2>
            <div className="space-y-2">
              {confirmedVideos.map((video, i) => (
                <VideoCard key={i} video={video} />
              ))}
            </div>
          </div>
        )}

        {/* YouTube videos — possibly related (outreach opportunity) */}
        {possibleVideos.length > 0 && (
          <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
            <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
              Outreach opportunities
            </h2>
            <div className="flex items-start gap-2 bg-primary/5 rounded-xl p-3 mb-4">
              <span className="material-symbols-outlined text-primary text-base mt-0.5 shrink-0">lightbulb</span>
              <p className="text-xs text-on-surface-variant">
                <span className="font-semibold text-on-surface">Tip: </span>
                These popular videos are related to your business. Drop a friendly comment mentioning your shop to reach their audience.
              </p>
            </div>
            <div className="space-y-2">
              {possibleVideos.slice(0, 5).map((video, i) => (
                <VideoCard key={i} video={video} muted />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ─── Right column: Missions panel ─── */}
      <div className="w-[380px] shrink-0 bg-surface-container-lowest rounded-xl shadow-ambient self-start sticky top-4 overflow-hidden">
        {/* Mission list / detail toggle */}
        {selectedMission ? (
          /* ── Mission detail view ── */
          <div className="p-5 overflow-y-auto max-h-[calc(100vh-120px)]">
            <button
              onClick={() => setSelectedMission(null)}
              className="flex items-center gap-1 text-sm text-on-surface-variant hover:text-on-surface mb-4"
            >
              <span className="material-symbols-outlined text-lg">
                arrow_back
              </span>
              Back to missions
            </button>

            <h3 className="font-headline font-extrabold text-on-surface text-lg">
              {selectedMission.title}
            </h3>
            <div className="flex items-center gap-3 mt-2 mb-5">
              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                  (
                    DIFFICULTY_STYLES[selectedMission.difficulty] ??
                    DIFFICULTY_STYLES.medium
                  ).bg
                } ${
                  (
                    DIFFICULTY_STYLES[selectedMission.difficulty] ??
                    DIFFICULTY_STYLES.medium
                  ).text
                }`}
              >
                {selectedMission.difficulty}
              </span>
              <span className="text-xs text-on-surface-variant">
                {selectedMission.estimated_minutes}m
              </span>
              <span className="text-xs text-on-surface-variant">
                Impact {selectedMission.impact_score}/10
              </span>
            </div>

            {/* Content drafts */}
            {missionContent && missionContent.length > 0 && (
              <div className="space-y-3 mb-5">
                <h4 className="font-headline font-bold text-on-surface text-sm">
                  Content Drafts
                </h4>
                {missionContent.map((item) => (
                  <ContentDraft
                    key={item.id}
                    id={item.id}
                    title={item.title}
                    content={item.body}
                    channel={item.channel}
                    copyCount={item.copy_count}
                  />
                ))}
              </div>
            )}

            {/* What to do */}
            <div className="mb-5">
              <h4 className="font-headline font-bold text-on-surface text-sm mb-2">
                What to do
              </h4>
              <p className="text-sm text-on-surface-variant leading-relaxed whitespace-pre-wrap">
                {selectedMission.description}
              </p>
            </div>

            {/* Mark as done */}
            {selectedMission.status !== "completed" && (
              <button
                onClick={() => markDone()}
                disabled={isPending}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {isPending ? "Updating…" : "Mark as done ✓"}
              </button>
            )}
            {selectedMission.status === "completed" && (
              <div className="flex items-center justify-center gap-2 py-3 rounded-xl bg-green-50 text-green-700 text-sm font-semibold">
                <span
                  className="material-symbols-outlined text-lg"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  check_circle
                </span>
                Completed
              </div>
            )}
          </div>
        ) : (
          /* ── Mission list view ── */
          <div className="p-5">
            <h2 className="font-headline font-extrabold text-on-surface text-lg mb-1">
              {label} Missions
            </h2>
            <p className="text-xs text-on-surface-variant mb-4">
              Actions to improve your {label.toLowerCase()} score
            </p>

            {/* AI-generated missions */}
            {missions.length > 0 && (
              <div className="space-y-2 mb-4">
                {missions.map((mission) => {
                  const diff =
                    DIFFICULTY_STYLES[mission.difficulty] ??
                    DIFFICULTY_STYLES.medium;
                  return (
                    <button
                      key={mission.id}
                      onClick={() => setSelectedMission(mission)}
                      className="w-full text-left rounded-xl p-4 bg-surface-container-low hover:bg-surface-container-high transition-colors group"
                    >
                      <h3 className="font-headline font-bold text-on-surface text-sm group-hover:text-primary transition-colors">
                        {mission.title}
                      </h3>
                      <p className="text-xs text-on-surface-variant mt-1 line-clamp-2">
                        {mission.description}
                      </p>
                      <div className="flex items-center gap-3 mt-2">
                        <span
                          className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${diff.bg} ${diff.text}`}
                        >
                          {mission.difficulty}
                        </span>
                        <span className="text-xs text-on-surface-variant">
                          {mission.estimated_minutes}m
                        </span>
                        <span className="text-xs text-on-surface-variant">
                          Impact {mission.impact_score}/10
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Quick actions from failing criteria — only shown when no AI missions exist */}
            {missions.length === 0 && failingCriteria.length > 0 && (
              <div className="space-y-2">
                {missions.length === 0 && (
                  <p className="text-xs text-on-surface-variant mb-2">
                    Quick actions based on your score:
                  </p>
                )}
                {failingCriteria.map((action, i) => (
                  <div
                    key={i}
                    className="rounded-xl p-4 bg-red-50/50"
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className="material-symbols-outlined text-red-500 text-base mt-0.5 shrink-0"
                        style={{ fontVariationSettings: "'FILL' 1" }}
                      >
                        priority_high
                      </span>
                      <div>
                        <h4 className="text-sm font-semibold text-on-surface">
                          {action.title}
                        </h4>
                        <p className="text-xs text-on-surface-variant mt-0.5">
                          {action.description}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {missions.length === 0 && failingCriteria.length === 0 && (
              <div className="text-center py-8">
                <span className="material-symbols-outlined text-3xl text-on-surface-variant/40 mb-2 block">
                  check_circle
                </span>
                <p className="text-sm text-on-surface-variant">
                  No missions needed — this area is performing well.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
      </div>{/* close flex row */}
    </div>
  );
}
