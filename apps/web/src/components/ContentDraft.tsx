import { useState } from "react";
import { apiFetch } from "../api/client";

interface ContentDraftProps {
  id: string;
  title: string;
  content: string;
  channel?: string;
  copyCount?: number;
}

export default function ContentDraft({
  id,
  title,
  content,
  channel,
  copyCount = 0,
}: ContentDraftProps) {
  const [copied, setCopied] = useState(false);
  const [count, setCount] = useState(copyCount);

  async function handleCopy() {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setCount((c) => c + 1);
    setTimeout(() => setCopied(false), 2000);

    // Track copy on backend
    apiFetch(`/content/${id}/copied`, { method: "POST" }).catch(() => {});
  }

  return (
    <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h4 className="font-headline font-extrabold text-on-surface text-base">
            {title}
          </h4>
          {channel && (
            <span className="text-xs text-on-surface-variant capitalize mt-0.5 block">
              {channel.replace("_", " ")}
            </span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
            copied
              ? "bg-green-100 text-green-700"
              : "bg-surface-container-low text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high"
          }`}
          title="Copy to clipboard"
        >
          <span className="material-symbols-outlined text-base">
            {copied ? "check" : "content_copy"}
          </span>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      <pre className="text-sm text-on-surface-variant whitespace-pre-wrap font-body leading-relaxed bg-surface-container-low rounded-lg p-4">
        {content}
      </pre>

      {count > 0 && (
        <p className="text-xs text-on-surface-variant mt-2">
          Copied {count} {count === 1 ? "time" : "times"}
        </p>
      )}
    </div>
  );
}
