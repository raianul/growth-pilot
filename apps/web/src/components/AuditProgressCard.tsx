const PHASE_LABELS: Record<string, string> = {
  google_maps: "Scanning Google Maps",
  reviews: "Analyzing customer reviews",
  website: "Analyzing your website",
  local_authority: "Checking local blogs & directories",
  youtube: "Searching YouTube",
  competitors: "Finding competitors",
  scoring: "Computing your scores",
  analysis: "AI gap analysis",
  missions: "Generating your missions",
  content_0: "Writing content draft 1",
  content_1: "Writing content draft 2",
  content_2: "Writing content draft 3",
};

const PHASE_ORDER = [
  "google_maps",
  "reviews",
  "website",
  "local_authority",
  "youtube",
  "competitors",
  "scoring",
  "analysis",
  "missions",
  "content_0",
  "content_1",
  "content_2",
];

type PhaseStatus = "done" | "running" | "pending" | "error";

interface AuditProgressCardProps {
  phaseProgress: Record<string, string> | null | undefined;
  currentPhase: string | null | undefined;
  totalScore?: number | null;
}

function PhaseIcon({ status }: { status: PhaseStatus }) {
  if (status === "done") {
    return (
      <span
        className="material-symbols-outlined text-xl leading-none"
        style={{ fontVariationSettings: "'FILL' 1", color: "#16a34a" }}
      >
        check_circle
      </span>
    );
  }
  if (status === "running") {
    return (
      <span
        className="material-symbols-outlined text-xl leading-none animate-spin text-primary"
        style={{ display: "inline-block" }}
      >
        pending
      </span>
    );
  }
  if (status === "error") {
    return (
      <span
        className="material-symbols-outlined text-xl leading-none"
        style={{ color: "#dc2626" }}
      >
        error
      </span>
    );
  }
  return (
    <span
      className="material-symbols-outlined text-xl leading-none"
      style={{ color: "#9ca3af" }}
    >
      radio_button_unchecked
    </span>
  );
}

export default function AuditProgressCard({
  phaseProgress,
  currentPhase,
  totalScore,
}: AuditProgressCardProps) {
  const progress = phaseProgress ?? {};

  const phases = PHASE_ORDER.map((key) => {
    const raw = progress[key] as string | undefined;
    let status: PhaseStatus = "pending";
    if (raw === "done" || raw === "completed") status = "done";
    else if (raw === "running" || key === currentPhase) status = "running";
    else if (raw === "error") status = "error";
    return { key, label: PHASE_LABELS[key] ?? key, status };
  });

  const doneCount = phases.filter((p) => p.status === "done").length;
  const progressPct = Math.round((doneCount / PHASE_ORDER.length) * 100);

  return (
    <div className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <span className="material-symbols-outlined text-2xl text-primary animate-pulse">
          radar
        </span>
        <div>
          <h3 className="font-headline font-extrabold text-on-surface text-lg leading-tight">
            Analyzing your online presence...
          </h3>
          <p className="text-on-surface-variant text-sm mt-0.5">
            This takes about 1–2 minutes
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-on-surface-variant text-xs font-medium">
            {doneCount} / {PHASE_ORDER.length} steps
          </span>
          <span className="text-on-surface-variant text-xs font-medium">
            {progressPct}%
          </span>
        </div>
        <div className="h-2 bg-surface-container-high rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Phase list */}
      <div className="space-y-3">
        {phases.map((phase) => (
          <div key={phase.key} className="flex items-center gap-3">
            <PhaseIcon status={phase.status} />
            <span
              className={[
                "text-sm font-body flex-1",
                phase.status === "done"
                  ? "text-green-700"
                  : phase.status === "running"
                    ? "text-on-surface font-medium"
                    : "text-on-surface-variant",
              ].join(" ")}
            >
              {phase.label}
            </span>
            {phase.status === "running" && (
              <span className="text-xs text-primary font-medium animate-pulse">running</span>
            )}
            {phase.status === "done" && (
              <span className="text-xs text-green-600 font-medium">done</span>
            )}
          </div>
        ))}
      </div>

      {/* Score reveal on completion */}
      {totalScore !== null && totalScore !== undefined && (
        <div className="mt-6 pt-6 border-t border-outline-variant/15 text-center">
          <p className="text-on-surface-variant text-sm mb-1">Your Growth Score</p>
          <p className="font-headline font-extrabold text-4xl text-primary">
            {totalScore}
          </p>
        </div>
      )}
    </div>
  );
}
