import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { useUIStore } from "../store/uiStore";

// ─── Mappings ─────────────────────────────────────────────────────────────────

const CHANNEL_DIMENSION: Record<string, string> = {
  google_maps: "google_maps",
  website: "website",
  social: "local_authority",
  youtube: "youtube",
  reddit: "local_authority",
  local_authority: "local_authority",
  blog: "website",
  seo: "website",
  reviews: "google_maps",
};

const DIMENSION_LABELS: Record<string, string> = {
  google_maps: "Google Maps",
  website: "Website & SEO",
  local_authority: "Local Authority",
  youtube: "YouTube",
  ai_readiness: "AI Readiness",
};

const DIMENSION_ICONS: Record<string, string> = {
  google_maps: "location_on",
  website: "language",
  local_authority: "public",
  youtube: "smart_display",
  ai_readiness: "psychology",
};

const DIFFICULTY_STYLES: Record<string, { bg: string; text: string }> = {
  easy: { bg: "bg-green-100", text: "text-green-700" },
  medium: { bg: "bg-yellow-100", text: "text-yellow-700" },
  hard: { bg: "bg-red-100", text: "text-red-600" },
};

// ─── Types ────────────────────────────────────────────────────────────────────

interface Mission {
  id: string;
  title: string;
  description?: string;
  channel: string;
  difficulty: "easy" | "medium" | "hard";
  estimated_minutes: number;
  impact_score: number;
  status: string;
  priority_score: number | null;
}

interface Outlet {
  id: string;
  outlet_name: string;
}

interface DashboardData {
  active_missions: Mission[];
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Missions() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { selectedOutletId } = useUIStore();

  const dimensionFilter = searchParams.get("dimension");
  const [activeFilter, setActiveFilter] = useState<string | null>(dimensionFilter);

  const { data: outlets } = useQuery<Outlet[]>({
    queryKey: ["outlets"],
    queryFn: () => apiFetch("/outlets"),
  });

  const outletId = selectedOutletId ?? outlets?.[0]?.id;

  const { data: dashboard, isLoading } = useQuery<DashboardData>({
    queryKey: ["dashboard", outletId],
    queryFn: () => apiFetch(`/outlets/${outletId}/dashboard`),
    enabled: !!outletId,
  });

  const missions = dashboard?.active_missions ?? [];

  // Group missions by dimension
  const grouped = missions.reduce<Record<string, Mission[]>>((acc, m) => {
    const dim = CHANNEL_DIMENSION[m.channel] ?? "other";
    (acc[dim] ??= []).push(m);
    return acc;
  }, {});

  // Filter
  const filteredGroups = activeFilter
    ? { [activeFilter]: grouped[activeFilter] ?? [] }
    : grouped;

  const dimensions = Object.keys(DIMENSION_LABELS);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Page header */}
      <div>
        <h1 className="font-headline font-extrabold text-on-surface text-3xl">Missions</h1>
        <p className="text-on-surface-variant mt-1">
          Your actionable growth tasks — sorted by impact
        </p>
      </div>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveFilter(null)}
          className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
            activeFilter === null
              ? "bg-primary text-white"
              : "bg-surface-container-low text-on-surface-variant hover:text-on-surface"
          }`}
        >
          All
        </button>
        {dimensions.map((dim) => (
            <button
              key={dim}
              onClick={() => setActiveFilter(activeFilter === dim ? null : dim)}
              className={`flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                activeFilter === dim
                  ? "bg-primary text-white"
                  : "bg-surface-container-low text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <span className="material-symbols-outlined text-sm">{DIMENSION_ICONS[dim]}</span>
              {DIMENSION_LABELS[dim]}
            </button>
        ))}
      </div>

      {/* Grouped mission list */}
      {Object.entries(filteredGroups).map(([dim, dimMissions]) =>
        dimMissions.length > 0 ? (
          <section key={dim}>
            <h2 className="font-headline font-bold text-on-surface text-lg flex items-center gap-2 mb-3">
              <span className="material-symbols-outlined text-primary">
                {DIMENSION_ICONS[dim] ?? "flag"}
              </span>
              {DIMENSION_LABELS[dim] ?? dim}
            </h2>
            <div className="space-y-3">
              {dimMissions.map((mission) => {
                const diff = DIFFICULTY_STYLES[mission.difficulty] ?? DIFFICULTY_STYLES.medium;
                return (
                  <button
                    key={mission.id}
                    onClick={() => navigate(`/missions/${mission.id}`)}
                    className="w-full text-left bg-surface-container-lowest rounded-xl p-5 shadow-ambient hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-headline font-bold text-on-surface">
                          {mission.title}
                        </h3>
                        {mission.description && (
                          <p className="text-sm text-on-surface-variant mt-1 line-clamp-2">
                            {mission.description}
                          </p>
                        )}
                        <div className="flex items-center gap-3 mt-2">
                          <span
                            className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${diff.bg} ${diff.text}`}
                          >
                            {mission.difficulty}
                          </span>
                          <span className="flex items-center gap-0.5 text-xs text-on-surface-variant">
                            <span className="material-symbols-outlined text-xs">schedule</span>
                            {mission.estimated_minutes}m
                          </span>
                          <span className="flex items-center gap-0.5 text-xs text-on-surface-variant">
                            <span className="material-symbols-outlined text-xs">bolt</span>
                            Impact {mission.impact_score}/10
                          </span>
                        </div>
                      </div>
                      <span className="material-symbols-outlined text-on-surface-variant shrink-0 mt-1">
                        chevron_right
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        ) : null,
      )}

      {/* Empty state */}
      {missions.length === 0 && (
        <div className="text-center py-12 bg-surface-container-lowest rounded-xl">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-3 block">
            checklist
          </span>
          <p className="text-on-surface-variant">
            No missions yet — run an audit to generate them.
          </p>
        </div>
      )}

      {/* Empty state for filtered dimension */}
      {activeFilter &&
        (grouped[activeFilter] ?? []).length === 0 && (
          <div className="text-center py-12 bg-surface-container-lowest rounded-xl">
            <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-3 block">
              {DIMENSION_ICONS[activeFilter] ?? "flag"}
            </span>
            <p className="text-on-surface-variant">
              No {DIMENSION_LABELS[activeFilter] ?? activeFilter} missions right now.
            </p>
            <p className="text-on-surface-variant/60 text-sm mt-2">
              This area may be performing well, or the next audit will generate tasks here.
            </p>
            <button
              onClick={() => setActiveFilter(null)}
              className="mt-4 text-sm text-primary font-medium hover:underline"
            >
              View all missions
            </button>
          </div>
        )}
    </div>
  );
}
