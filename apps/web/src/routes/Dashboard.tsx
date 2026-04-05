import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { useUIStore } from "../store/uiStore";
import MissionCard from "../components/MissionCard";
import AuditProgressCard from "../components/AuditProgressCard";
import type { Dimension } from "../components/DimensionCard";

interface Outlet {
  id: string;
  outlet_name: string;
  city: string;
}

interface Audit {
  id: string;
  week_number: number;
  status: string;
  total_score: number | null;
  score_delta: number | null;
  current_phase: string | null;
  phase_progress: Record<string, string> | null;
  created_at: string;
  completed_at: string | null;
  dimensions: Dimension[];
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
  sort_order: number;
  priority_score: number | null;
}

interface DashboardData {
  outlet_id: string;
  outlet_name: string;
  organization_name: string;
  latest_audit: Audit | null;
  active_missions: Mission[];
  next_audit_at: string | null;
}

// ─── Plain-language presence status ──────────────────────────────────────────

function getPresenceStatus(dim: Dimension): {
  icon: string;
  color: string;
  label: string;
  detail: string;
} {
  const score = dim.score;
  const data = (dim.raw_data ?? {}) as Record<string, unknown>;

  if (dim.dimension === "google_maps") {
    const rating = data.rating as number | undefined;
    const reviews = data.reviews as number | undefined;
    const position = data.position as number | undefined;
    if (score >= 70)
      return {
        icon: "check_circle",
        color: "text-green-600",
        label: "Google Maps",
        detail: `${rating ?? "?"}★ rating · ${reviews ?? "?"} reviews · #${position ?? "?"} in your area`,
      };
    if (score >= 40)
      return {
        icon: "warning",
        color: "text-yellow-600",
        label: "Google Maps",
        detail: `${rating ?? "?"}★ rating · ${reviews ?? "?"} reviews — needs improvement`,
      };
    return {
      icon: "error",
      color: "text-red-500",
      label: "Google Maps",
      detail: "Not found or very low visibility",
    };
  }

  if (dim.dimension === "website") {
    const content = data.content as string | undefined;
    const hasContent = (content?.length ?? 0) > 500;
    if (score >= 70)
      return {
        icon: "check_circle",
        color: "text-green-600",
        label: "Website",
        detail: "Content and SEO basics in place",
      };
    if (hasContent)
      return {
        icon: "warning",
        color: "text-yellow-600",
        label: "Website",
        detail: "Has content but missing SEO essentials",
      };
    return {
      icon: "error",
      color: "text-red-500",
      label: "Website",
      detail: "No content or major SEO issues",
    };
  }

  if (dim.dimension === "local_authority") {
    const mentions = (data.mention_count as number | undefined) ?? 0;
    const onList = data.on_best_of_list as boolean | undefined;
    if (mentions >= 5)
      return {
        icon: "check_circle",
        color: "text-green-600",
        label: "Local Presence",
        detail: `Mentioned on ${mentions} local sites${onList ? " · Featured on a 'best of' list" : ""}`,
      };
    if (mentions >= 1)
      return {
        icon: "warning",
        color: "text-yellow-600",
        label: "Local Presence",
        detail: `${mentions} local mention${mentions > 1 ? "s" : ""} — could use more`,
      };
    return {
      icon: "error",
      color: "text-red-500",
      label: "Local Presence",
      detail: "Not mentioned on any local blogs or directories",
    };
  }

  if (dim.dimension === "youtube") {
    const count =
      ((data.video_count as number | undefined) ??
        (data.confirmed_count as number | undefined) ??
        0);
    const hasChannel = data.has_own_channel as boolean | undefined;
    if (hasChannel)
      return {
        icon: "check_circle",
        color: "text-green-600",
        label: "YouTube",
        detail: `Own channel + ${count} video${count !== 1 ? "s" : ""} mentioning you`,
      };
    if (count > 0)
      return {
        icon: "warning",
        color: "text-yellow-600",
        label: "YouTube",
        detail: `${count} video${count > 1 ? "s" : ""} mention you but no own channel`,
      };
    return {
      icon: "error",
      color: "text-red-500",
      label: "YouTube",
      detail: "No YouTube presence",
    };
  }

  if (dim.dimension === "ai_readiness") {
    if (score >= 70)
      return {
        icon: "check_circle",
        color: "text-green-600",
        label: "AI Visibility",
        detail: "AI assistants can find and recommend you",
      };
    if (score >= 40)
      return {
        icon: "warning",
        color: "text-yellow-600",
        label: "AI Visibility",
        detail: "Partially ready — some signals missing",
      };
    return {
      icon: "error",
      color: "text-red-500",
      label: "AI Visibility",
      detail: "AI assistants can't recommend you yet",
    };
  }

  return { icon: "help", color: "text-gray-400", label: dim.dimension, detail: "" };
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { selectedOutletId, setSelectedOutlet } = useUIStore();
  const queryClient = useQueryClient();

  const [showMore, setShowMore] = useState(false);
  const [auditRunning, setAuditRunning] = useState(false);
  const [runningAuditId, setRunningAuditId] = useState<string | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);

  const { data: outlets, isLoading: outletsLoading } = useQuery({
    queryKey: ["outlets"],
    queryFn: () => apiFetch<Outlet[]>("/outlets"),
  });

  // Default to first outlet if none selected
  useEffect(() => {
    if (outlets && outlets.length > 0 && !selectedOutletId) {
      setSelectedOutlet(outlets[0].id);
    }
  }, [outlets, selectedOutletId, setSelectedOutlet]);

  const outletId = selectedOutletId ?? outlets?.[0]?.id;

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["dashboard", outletId],
    queryFn: () => apiFetch<DashboardData>(`/outlets/${outletId}/dashboard`),
    enabled: !!outletId,
    // Poll every 3 seconds while an audit is running to pick up phase_progress
    refetchInterval: auditRunning ? 3000 : false,
  });

  const handleAuditComplete = useCallback(() => {
    setAuditRunning(false);
    setRunningAuditId(null);
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }, [queryClient]);

  // Detect completion via polling
  useEffect(() => {
    if (auditRunning && dashboard?.latest_audit?.status === "completed") {
      handleAuditComplete();
    }
  }, [dashboard, auditRunning, handleAuditComplete]);

  async function handleRunAudit() {
    if (!outletId) return;
    setAuditError(null);
    try {
      const result = await apiFetch<{ audit_id: string }>(
        `/outlets/${outletId}/audit`,
        { method: "POST" },
      );
      setRunningAuditId(result.audit_id);
      setAuditRunning(true);
    } catch (err) {
      setAuditError(
        err instanceof Error ? err.message : "Failed to start audit",
      );
    }
  }

  if (outletsLoading || dashLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="text-center py-16">
        <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-4 block">
          business
        </span>
        <p className="text-on-surface-variant font-body">
          No outlet found. Complete onboarding to get started.
        </p>
      </div>
    );
  }

  const audit = dashboard.latest_audit;
  const missions = dashboard.active_missions ?? [];
  const pendingMissions = missions.filter(
    (m) => m.status === "pending" || m.status === "active",
  );
  const completedMissions = missions.filter(
    (m) => m.status !== "pending" && m.status !== "active",
  );
  const topMissions = pendingMissions.slice(0, 3);
  const moreMissions = pendingMissions.slice(3);

  // Derive progress from the latest audit — either the one we triggered or any running audit
  const latestAudit = dashboard?.latest_audit;
  const isAuditInProgress =
    latestAudit && !["completed", "failed"].includes(latestAudit.status);
  const progressAudit =
    auditRunning || isAuditInProgress ? latestAudit : null;

  // Suppress unused variable warning — runningAuditId is set for potential future use
  void runningAuditId;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="space-y-8 max-w-5xl p-8">
        {/* Hero */}
        <div className="bg-gradient-to-br from-primary to-primary-container rounded-xl p-8 text-white shadow-ambient">
          <h1 className="font-headline font-extrabold text-3xl">
            {dashboard.organization_name}
          </h1>
          <p className="text-white/70 mt-1">{dashboard.outlet_name}</p>
          {dashboard.next_audit_at && !auditRunning && (
            <p className="text-white/60 text-sm mt-2">
              Next audit:{" "}
              {new Date(dashboard.next_audit_at).toLocaleDateString()}
            </p>
          )}
          {/* Run audit button — shown when audit exists and not currently running */}
          {audit && !auditRunning && (
            <button
              onClick={handleRunAudit}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/20 text-white text-sm font-medium hover:bg-white/30 transition-colors mt-4"
            >
              <span className="material-symbols-outlined text-lg">refresh</span>
              Run audit
            </button>
          )}
          {auditRunning && (
            <div className="flex items-center gap-2 mt-4 text-white/80">
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span className="text-sm font-medium">Auditing…</span>
            </div>
          )}
        </div>

        {/* Error banner */}
        {auditError && (
          <div className="bg-red-50 rounded-xl p-4 flex items-center gap-3">
            <span className="material-symbols-outlined text-red-500">
              error
            </span>
            <p className="text-red-700 text-sm">{auditError}</p>
            <button
              onClick={() => setAuditError(null)}
              className="ml-auto text-red-400 hover:text-red-600"
            >
              <span className="material-symbols-outlined text-lg">close</span>
            </button>
          </div>
        )}

        {/* Main content area — progress card | first audit CTA | normal dashboard */}
        {(auditRunning || isAuditInProgress) && progressAudit ? (
          <AuditProgressCard
            phaseProgress={progressAudit.phase_progress}
            currentPhase={progressAudit.current_phase}
            totalScore={
              progressAudit.status === "completed"
                ? progressAudit.total_score
                : undefined
            }
          />
        ) : !audit ? (
          /* ── No audit yet — run first audit CTA ── */
          <div className="bg-gradient-to-br from-primary to-primary-container rounded-xl p-8 text-white text-center">
            <span className="material-symbols-outlined text-5xl mb-4 block">
              radar
            </span>
            <h2 className="font-headline font-extrabold text-2xl mb-2">
              Ready to grow?
            </h2>
            <p className="text-white/80 mb-6">
              Run your first audit to discover your online visibility and get
              personalized missions.
            </p>
            <button
              onClick={handleRunAudit}
              className="bg-white text-primary font-semibold px-6 py-3 rounded-xl hover:opacity-90 transition-opacity"
            >
              Run first audit →
            </button>
          </div>
        ) : (
          /* ── Normal dashboard ── */
          <>
            {/* Your Online Presence */}
            {audit.dimensions.length > 0 && (
              <section>
                <h2 className="font-headline font-extrabold text-on-surface text-xl mb-4">
                  Your Online Presence
                </h2>
                <div className="space-y-3">
                  {[...audit.dimensions]
                    .sort((a, b) => a.score - b.score) // worst first
                    .map((dim) => {
                      const status = getPresenceStatus(dim);
                      const detail = dim.is_stale
                        ? `${status.detail}${status.detail ? " " : ""}(outdated)`
                        : status.detail;
                      return (
                        <a
                          key={dim.dimension}
                          href={`/dimensions/${dim.dimension}`}
                          className="flex items-start gap-3 bg-surface-container-lowest rounded-xl p-4 shadow-ambient hover:shadow-md transition-shadow group"
                        >
                          <span
                            className={`material-symbols-outlined text-xl mt-0.5 shrink-0 ${status.color}`}
                            style={{ fontVariationSettings: "'FILL' 1" }}
                          >
                            {status.icon}
                          </span>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-headline font-bold text-on-surface group-hover:text-primary transition-colors">
                              {status.label}
                            </h3>
                            <p className="text-sm text-on-surface-variant mt-0.5">
                              {detail}
                            </p>
                          </div>
                          <span className="material-symbols-outlined text-on-surface-variant shrink-0">
                            chevron_right
                          </span>
                        </a>
                      );
                    })}
                </div>
              </section>
            )}

            {/* Top priority missions */}
            {topMissions.length > 0 && (
              <section>
                <h2 className="font-headline font-extrabold text-on-surface text-xl mb-1">
                  Top Priorities
                </h2>
                <p className="text-on-surface-variant text-sm mb-4">
                  Your 3 highest-impact actions this week
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {topMissions.map((mission, idx) => (
                    <MissionCard
                      key={mission.id}
                      mission={mission}
                      rank={idx + 1}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* More missions — collapsed by default */}
            {moreMissions.length > 0 && (
              <section>
                <button
                  onClick={() => setShowMore(!showMore)}
                  className="text-sm text-primary font-medium flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-lg">
                    {showMore ? "expand_less" : "expand_more"}
                  </span>
                  {showMore
                    ? "Show less"
                    : `${moreMissions.length} more mission${moreMissions.length !== 1 ? "s" : ""}`}
                </button>
                {showMore && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-3">
                    {moreMissions.map((mission) => (
                      <MissionCard key={mission.id} mission={mission} />
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* Completed missions */}
            {completedMissions.length > 0 && (
              <section>
                <h2 className="font-headline font-extrabold text-on-surface text-xl mb-4">
                  Completed Missions
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {completedMissions.map((mission) => (
                    <MissionCard key={mission.id} mission={mission} />
                  ))}
                </div>
              </section>
            )}

            {missions.length === 0 && (
              <div className="text-center py-12 bg-surface-container-lowest rounded-xl shadow-ambient">
                <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-3 block">
                  checklist
                </span>
                <p className="text-on-surface-variant">
                  No missions yet — your next audit will generate them.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
