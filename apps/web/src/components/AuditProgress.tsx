import { useQueryClient } from "@tanstack/react-query";
import { useAuditStream, type AuditStreamEvent } from "../hooks/useAuditStream";

const PHASE_LABELS: Record<string, string> = {
  scraping: "Scraping website",
  maps_rank: "Checking Google Maps rank",
  competitors: "Discovering competitors",
  otterly: "Monitoring AI citations",
  reddit: "Scanning Reddit",
  youtube: "Checking YouTube presence",
  analysis: "Analyzing with AI",
  missions: "Generating missions",
};

interface AuditProgressProps {
  auditId: string | null;
  onComplete?: () => void;
  onError?: (msg: string) => void;
}

export default function AuditProgress({
  auditId,
  onComplete,
  onError,
}: AuditProgressProps) {
  const queryClient = useQueryClient();
  const events =
    queryClient.getQueryData<AuditStreamEvent[]>(["audit-stream", auditId]) ??
    [];

  useAuditStream({ auditId, onComplete, onError });

  const phases = Object.keys(PHASE_LABELS);

  return (
    <div className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient space-y-4">
      <h3 className="font-headline font-extrabold text-on-surface text-lg">
        Running audit…
      </h3>
      <ul className="space-y-3">
        {phases.map((phase) => {
          const event = events.find((e) => e.data.phase === phase);
          const status = event?.data.status ?? "pending";

          return (
            <li key={phase} className="flex items-center gap-3">
              {/* Status icon */}
              <div className="w-6 h-6 flex-shrink-0 flex items-center justify-center">
                {status === "done" && (
                  <span className="material-symbols-outlined text-primary text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                    check_circle
                  </span>
                )}
                {status === "running" && (
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                )}
                {status === "error" && (
                  <span className="material-symbols-outlined text-red-500 text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                    error
                  </span>
                )}
                {status === "pending" && (
                  <div className="w-4 h-4 rounded-full bg-surface-container-high" />
                )}
              </div>

              {/* Label */}
              <span
                className={`text-sm font-medium ${
                  status === "done"
                    ? "text-on-surface"
                    : status === "running"
                      ? "text-primary"
                      : "text-on-surface-variant"
                }`}
              >
                {PHASE_LABELS[phase]}
              </span>

              {/* Progress bar for running */}
              {status === "running" && event?.data.progress !== undefined && (
                <div className="ml-auto w-20 h-1.5 bg-surface-container-high rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${event.data.progress}%` }}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
