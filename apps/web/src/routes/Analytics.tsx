import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { useUIStore } from "../store/uiStore";

interface Outlet {
  id: string;
  outlet_name: string;
}

interface Dimension {
  dimension: string;
  score: number;
  weight: number;
  is_stale: boolean;
}

interface ScoreHistoryItem {
  week_number: number;
  score: number;
  dimensions: Dimension[];
}

const DIMENSION_LABELS: Record<string, string> = {
  google_maps: "Google Maps",
  website: "Website & SEO",
  local_authority: "Local Authority",
  youtube: "YouTube",
  ai_readiness: "AI Readiness",
};

function getDimensionStatus(score: number): {
  icon: string;
  color: string;
  label: string;
} {
  if (score >= 70)
    return { icon: "check_circle", color: "text-green-600", label: "Good" };
  if (score >= 40)
    return { icon: "warning", color: "text-yellow-600", label: "Needs work" };
  return { icon: "error", color: "text-red-500", label: "Needs attention" };
}

function getWeekSummary(
  current: ScoreHistoryItem,
  previous: ScoreHistoryItem | undefined,
): { icon: string; color: string; text: string }[] {
  if (!previous) {
    // First week — just show statuses
    return current.dimensions.map((dim) => {
      const s = getDimensionStatus(dim.score);
      return {
        icon: s.icon,
        color: s.color,
        text: DIMENSION_LABELS[dim.dimension] ?? dim.dimension,
      };
    });
  }

  return current.dimensions.map((dim) => {
    const prevDim = previous.dimensions.find(
      (d) => d.dimension === dim.dimension,
    );
    const label = DIMENSION_LABELS[dim.dimension] ?? dim.dimension;
    const delta = prevDim ? dim.score - prevDim.score : 0;

    if (delta > 5)
      return { icon: "trending_up", color: "text-green-600", text: `${label} — improved` };
    if (delta < -5)
      return { icon: "trending_down", color: "text-red-500", text: `${label} — declined` };
    return { icon: "remove", color: "text-on-surface-variant", text: `${label} — unchanged` };
  });
}

export default function Analytics() {
  const { selectedOutletId } = useUIStore();

  const { data: outlets, isLoading: outletsLoading } = useQuery({
    queryKey: ["outlets"],
    queryFn: () => apiFetch<Outlet[]>("/outlets"),
  });

  const outletId = selectedOutletId ?? outlets?.[0]?.id;

  const { data: history, isLoading } = useQuery({
    queryKey: ["analytics", outletId],
    queryFn: () =>
      apiFetch<ScoreHistoryItem[]>(`/outlets/${outletId}/scores/history`),
    enabled: !!outletId,
  });

  if (outletsLoading || isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="font-headline font-extrabold text-on-surface text-3xl">
        Analytics
      </h1>
      <p className="text-on-surface-variant">
        How your online presence has changed week by week.
      </p>

      {!history || history.length === 0 ? (
        <div className="text-center py-12 bg-surface-container-lowest rounded-xl shadow-ambient">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-3 block">
            bar_chart
          </span>
          <p className="text-on-surface-variant">
            No audit history yet. Complete your first audit to see analytics.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {[...history]
            .sort((a, b) => b.week_number - a.week_number) // newest first
            .map((item, idx, arr) => {
              const previous = arr[idx + 1]; // older week
              const changes = getWeekSummary(item, previous);

              return (
                <div
                  key={item.week_number}
                  className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient"
                >
                  <p className="font-headline font-extrabold text-on-surface text-lg mb-3">
                    Week {item.week_number}
                    {idx === 0 && (
                      <span className="ml-2 text-xs font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full">
                        Latest
                      </span>
                    )}
                  </p>
                  <div className="space-y-1.5">
                    {changes.map((change, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span
                          className={`material-symbols-outlined text-base shrink-0 ${change.color}`}
                          style={{ fontVariationSettings: "'FILL' 1" }}
                        >
                          {change.icon}
                        </span>
                        <span className="text-sm text-on-surface-variant">
                          {change.text}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
