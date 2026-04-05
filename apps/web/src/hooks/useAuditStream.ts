import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "../api/client";

export interface AuditPhaseUpdate {
  phase: string;
  status: "pending" | "running" | "done" | "error";
  message?: string;
  progress?: number;
}

export interface AuditStreamEvent {
  type: "phase_update" | "complete" | "error";
  audit_id: string;
  data: AuditPhaseUpdate;
}

interface UseAuditStreamOptions {
  auditId: string | null;
  onComplete?: () => void;
  onError?: (message: string) => void;
}

export function useAuditStream({
  auditId,
  onComplete,
  onError,
}: UseAuditStreamOptions) {
  const queryClient = useQueryClient();
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!auditId) return;

    let cancelled = false;

    async function connect() {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (cancelled || !auditId) return;

      const url = `/api/v1/audits/${auditId}/stream${
        session?.access_token
          ? `?token=${encodeURIComponent(session.access_token)}`
          : ""
      }`;

      const es = new EventSource(url);
      esRef.current = es;

      es.addEventListener("phase_update", (e: MessageEvent) => {
        const event: AuditStreamEvent = JSON.parse(e.data);
        queryClient.setQueryData<AuditStreamEvent[]>(
          ["audit-stream", auditId],
          (prev = []) => {
            const idx = prev.findIndex(
              (p) => p.data.phase === event.data.phase,
            );
            if (idx === -1) return [...prev, event];
            const next = [...prev];
            next[idx] = event;
            return next;
          },
        );
      });

      es.addEventListener("complete", () => {
        es.close();
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        onComplete?.();
      });

      es.addEventListener("error", (e: MessageEvent) => {
        const msg = e.data ? (JSON.parse(e.data) as { message: string }).message : "Stream error";
        onError?.(msg);
        es.close();
      });

      es.onerror = () => {
        es.close();
      };
    }

    void connect();

    return () => {
      cancelled = true;
      esRef.current?.close();
    };
  }, [auditId, queryClient, onComplete, onError]);
}
