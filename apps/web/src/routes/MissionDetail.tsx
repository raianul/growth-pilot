import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { useUIStore } from "../store/uiStore";
import ContentDraft from "../components/ContentDraft";
import { getDimensionBreakdown, DIMENSION_LABELS, getStatusLabel } from "../components/DimensionCard";

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
  difficulty: string;
  estimated_minutes: number;
  impact_score: number;
  status: string;
  sort_order: number;
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

interface ContentItem {
  id: string;
  channel: string;
  title: string;
  body: string;
  metadata: Record<string, unknown> | null;
  copy_count: number;
}

const CHANNEL_DIMENSION: Record<string, string> = {
  google_maps: "google_maps",
  website: "website",
  social: "local_authority",
  youtube: "youtube",
  reddit: "local_authority",
  local_authority: "local_authority",
};

const canMarkDone = (status: string) => status !== "completed";

export default function MissionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedOutletId } = useUIStore();

  const { data: outlets } = useQuery({
    queryKey: ["outlets"],
    queryFn: () => apiFetch<Outlet[]>("/outlets"),
  });
  const outletId = selectedOutletId ?? outlets?.[0]?.id;

  const { data: dashboard } = useQuery({
    queryKey: ["dashboard", outletId],
    queryFn: () => apiFetch<DashboardData>(`/outlets/${outletId}/dashboard`),
    enabled: !!outletId,
  });

  const mission = dashboard?.active_missions?.find((m) => m.id === id);

  // Find the dimension that matches this mission's channel
  const dimensionKey = mission ? CHANNEL_DIMENSION[mission.channel] : null;
  const dimension = dimensionKey
    ? dashboard?.latest_audit?.dimensions?.find(
        (d) => d.dimension === dimensionKey,
      )
    : null;

  const { data: content, isLoading: contentLoading } = useQuery({
    queryKey: ["mission-content", id],
    queryFn: () => apiFetch<ContentItem[]>(`/missions/${id}/content`),
    enabled: !!id,
  });

  const { mutate: updateStatus, isPending } = useMutation({
    mutationFn: (status: string) =>
      apiFetch(`/missions/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  if (!dashboard) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!mission) {
    return (
      <div className="text-center py-16 text-on-surface-variant">
        Mission not found.
      </div>
    );
  }

  // Get dimension breakdown if available
  const dimBreakdown = dimension
    ? getDimensionBreakdown(dimension.dimension, dimension.raw_data)
    : null;
  const dimLabel = dimensionKey ? DIMENSION_LABELS[dimensionKey] : null;
  const dimStatus = dimension ? getStatusLabel(dimension.score) : null;

  // Extract sources from dimension raw_data
  const sources = (dimension?.raw_data?.sources ?? []) as {
    title: string;
    url: string;
    snippet: string;
  }[];
  const videos = (dimension?.raw_data?.videos ?? []) as {
    title: string;
    video_id: string;
    channel: string;
  }[];

  return (
    <div className="max-w-3xl space-y-6">
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-on-surface-variant hover:text-on-surface transition-colors text-sm font-medium"
      >
        <span className="material-symbols-outlined text-lg">arrow_back</span>
        Back
      </button>

      {/* Mission header */}
      <div className="bg-gradient-to-br from-primary to-primary-container rounded-xl p-6 text-white">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-white/70 text-sm capitalize">
                {mission.channel.replace("_", " ")}
              </span>
              <span className="text-white/40">·</span>
              <span className="text-white/70 text-sm capitalize">
                {mission.difficulty}
              </span>
            </div>
            <h1 className="font-headline font-extrabold text-2xl">
              {mission.title}
            </h1>
          </div>
          <div className="flex flex-col items-end gap-1 text-sm text-white/70">
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined text-base">
                schedule
              </span>
              {mission.estimated_minutes}m
            </span>
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined text-base">bolt</span>
              Impact {mission.impact_score}/10
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 mt-4">
          <span className="px-3 py-1 rounded-full bg-white/20 text-white text-xs font-semibold capitalize">
            {mission.status === "completed" ? "Completed" : "Pending"}
          </span>
          {canMarkDone(mission.status) && (
            <button
              onClick={() => updateStatus("completed")}
              disabled={isPending}
              className="px-4 py-2 rounded-lg bg-white text-primary text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {isPending ? "Updating…" : "Mark as done ✓"}
            </button>
          )}
        </div>
      </div>

      {/* Content drafts — main value, shown first */}
      {contentLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-6 h-6 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : content && content.length > 0 ? (
        <section>
          <h2 className="font-headline font-extrabold text-on-surface text-xl mb-4">
            Content Drafts
          </h2>
          <div className="space-y-4">
            {content.map((item) => (
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
        </section>
      ) : null}

      {/* What to do */}
      <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
        <h2 className="font-headline font-extrabold text-on-surface text-lg mb-3">
          What to do
        </h2>
        <p className="text-on-surface-variant text-sm leading-relaxed whitespace-pre-wrap">
          {mission.description}
        </p>
      </div>

      {/* Dimension context — score breakdown */}
      {dimension && dimBreakdown && dimLabel && dimStatus && (
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-headline font-extrabold text-on-surface text-lg">
              {dimLabel} Score
            </h2>
            <span className={`text-sm font-semibold ${dimStatus.color}`}>
              {dimension.score}/100 · {dimStatus.label}
            </span>
          </div>

          <ul className="space-y-2">
            {dimBreakdown.criteria.map((c, i) => (
              <li key={i} className="flex items-start gap-2">
                <span
                  className={`material-symbols-outlined text-base mt-0.5 shrink-0 ${
                    c.met ? "text-primary" : "text-red-500"
                  }`}
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  {c.met ? "check_circle" : "cancel"}
                </span>
                <span className="text-sm text-on-surface flex-1">
                  {c.label}
                </span>
                <span
                  className={`text-xs font-semibold shrink-0 ${
                    c.met ? "text-primary" : "text-on-surface-variant"
                  }`}
                >
                  {c.met ? `+${c.points}` : "+0"}
                </span>
              </li>
            ))}
          </ul>

          {dimBreakdown.tip && (
            <div className="flex items-start gap-2 bg-primary/5 rounded-xl p-3 mt-4">
              <span className="material-symbols-outlined text-primary text-base mt-0.5 shrink-0">
                lightbulb
              </span>
              <p className="text-xs text-on-surface-variant">
                <span className="font-semibold text-on-surface">Tip: </span>
                {dimBreakdown.tip}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Source links — local authority mentions */}
      {sources.length > 0 && (
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
          <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
            Where you're mentioned
          </h2>
          <div className="space-y-2">
            {sources.slice(0, 8).map((source, i) => (
              <a
                key={i}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-2.5 rounded-xl p-3 hover:bg-surface-container-low transition-colors group"
              >
                <span className="material-symbols-outlined text-primary text-base mt-0.5 shrink-0">
                  open_in_new
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors line-clamp-1">
                    {source.title}
                  </p>
                  {source.snippet && (
                    <p className="text-xs text-on-surface-variant mt-0.5 line-clamp-2">
                      {source.snippet}
                    </p>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* YouTube videos */}
      {videos.length > 0 && (
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
          <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
            Videos mentioning your business
          </h2>
          <div className="space-y-2">
            {videos.slice(0, 8).map((video, i) => (
              <a
                key={i}
                href={`https://youtube.com/watch?v=${video.video_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-2.5 rounded-xl p-3 hover:bg-surface-container-low transition-colors group"
              >
                <span className="material-symbols-outlined text-red-500 text-base mt-0.5 shrink-0">
                  smart_display
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors line-clamp-1">
                    {video.title}
                  </p>
                  {video.channel && (
                    <p className="text-xs text-on-surface-variant mt-0.5">
                      {video.channel}
                    </p>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
