import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { useUIStore } from "../store/uiStore";
import ScoreRing from "../components/ScoreRing";

interface Outlet {
  id: string;
  outlet_name: string;
}

interface Competitor {
  id: string;
  business_name: string;
  google_place_id: string | null;
  source: string;
  latest_score: number | null;
  gap_analysis: Record<string, string> | null;
}

export default function Competitors() {
  const { selectedOutletId } = useUIStore();

  const { data: outlets, isLoading: outletsLoading } = useQuery({
    queryKey: ["outlets"],
    queryFn: () => apiFetch<Outlet[]>("/outlets"),
  });

  const outletId = selectedOutletId ?? outlets?.[0]?.id;

  const { data: competitors, isLoading } = useQuery({
    queryKey: ["competitors", outletId],
    queryFn: () => apiFetch<Competitor[]>(`/outlets/${outletId}/competitors`),
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
        Competitors
      </h1>
      <p className="text-on-surface-variant">
        Track how your competitors rank in your local market.
      </p>

      {!competitors || competitors.length === 0 ? (
        <div className="text-center py-12 bg-surface-container-lowest rounded-xl shadow-ambient">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-3 block">
            groups
          </span>
          <p className="text-on-surface-variant">
            No competitors discovered yet. Run an audit to find them.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {competitors.map((c, idx) => (
            <div
              key={c.id}
              className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient flex items-center gap-6"
            >
              {/* Rank */}
              <div className="w-8 h-8 rounded-full bg-surface-container-low flex items-center justify-center flex-shrink-0">
                <span className="font-headline font-extrabold text-on-surface-variant text-sm">
                  {idx + 1}
                </span>
              </div>

              {/* Name + meta */}
              <div className="flex-1 min-w-0">
                <h3 className="font-headline font-extrabold text-on-surface text-base truncate">
                  {c.business_name}
                </h3>
                <div className="flex items-center gap-4 mt-1 text-xs text-on-surface-variant">
                  <span
                    className={`px-2 py-0.5 rounded-full ${
                      c.source === "manual"
                        ? "bg-primary/10 text-primary"
                        : "bg-surface-container-low"
                    }`}
                  >
                    {c.source === "manual" ? "Manual" : "Auto-discovered"}
                  </span>
                  {c.gap_analysis?.rating != null && (
                    <span className="flex items-center gap-1">
                      <span
                        className="material-symbols-outlined text-sm text-yellow-500"
                        style={{ fontVariationSettings: "'FILL' 1" }}
                      >
                        star
                      </span>
                      {Number(c.gap_analysis.rating).toFixed(1)}
                    </span>
                  )}
                  {c.gap_analysis?.reviews != null && (
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">
                        reviews
                      </span>
                      {c.gap_analysis.reviews} reviews
                    </span>
                  )}
                  {c.gap_analysis?.position != null && (
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">
                        location_on
                      </span>
                      Maps #{c.gap_analysis.position}
                    </span>
                  )}
                </div>
              </div>

              {/* Score */}
              {c.latest_score != null && (
                <ScoreRing score={c.latest_score} size={64} strokeWidth={6} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
