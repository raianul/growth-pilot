import { useState } from "react";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

function Check({ yes }: { yes: boolean }) {
  return yes
    ? <Icon name="check_circle" className="text-green-600 text-lg" />
    : <Icon name="cancel" className="text-red-400 text-lg" />;
}

/* ------------------------------------------------------------------ */
/*  1. GrowthPilot Score                                               */
/* ------------------------------------------------------------------ */

export function GrowthPilotScore({ score }: { score: { score: number; max: number; factors: { name: string; score: number; weight: number; detail: string }[] } }) {
  const pct = (score.score / score.max) * 100;

  return (
    <div className="rounded-lg bg-gradient-to-br from-primary to-primary-container p-6 shadow-ambient text-white">
      <div className="flex items-center gap-6">
        {/* Score circle */}
        <div className="relative h-24 w-24 shrink-0">
          <svg viewBox="0 0 36 36" className="h-24 w-24 -rotate-90">
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="3" />
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="white" strokeWidth="3" strokeDasharray={`${pct}, 100`} strokeLinecap="round" />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-headline text-2xl font-extrabold">{score.score}</span>
            <span className="text-xs text-white/70">/ {score.max}</span>
          </div>
        </div>

        <div>
          <div className="font-headline text-lg font-extrabold">GrowthPilot Score</div>
          <p className="text-sm text-white/70 mt-1">
            {score.score >= 3.5 ? "Strong online presence — keep building on this."
             : score.score >= 2.5 ? "Good foundation — a few improvements will make a big difference."
             : "Lots of room to grow — let's fix the basics first."}
          </p>
        </div>
      </div>

      {/* Factor breakdown */}
      <div className="mt-5 grid grid-cols-2 sm:grid-cols-5 gap-2">
        {score.factors.slice(0, 5).map((f, i) => (
          <div key={i} className="rounded-lg bg-white/10 px-2.5 py-2 text-center">
            <div className={`font-headline font-extrabold text-sm ${f.score >= 3 ? "text-white" : "text-white/50"}`}>
              {f.score}/5
            </div>
            <div className="text-xs text-white/60 mt-0.5 truncate">{f.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  2. Competitor Scorecard                                            */
/* ------------------------------------------------------------------ */

type ScorecardEntry = {
  name: string; is_owner: boolean; rating: number | null; review_count: number;
  website: boolean; facebook: boolean; instagram: boolean; tiktok: boolean; foodpanda: boolean;
};

export function CompetitorScorecard({ scorecard }: { scorecard: ScorecardEntry[] }) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
      <div className="flex items-center gap-2 mb-1">
        <div className="font-headline font-extrabold text-on-surface">Competitor Scorecard</div>
        <div className="relative">
          <button
            onClick={() => setShowTooltip((v) => !v)}
            aria-label="About this data"
            className="flex h-7 w-7 items-center justify-center rounded-full hover:bg-surface-container-low transition"
          >
            <Icon name="info" className="text-base text-on-surface-variant/50" />
          </button>
          {showTooltip && (
            <div className="absolute left-0 top-full mt-1 z-50 rounded-lg bg-surface-container-lowest shadow-ambient p-3 w-64">
              <p className="text-xs text-on-surface-variant">This data is collected from publicly available Google search results. Some links may exist but are not yet indexed by Google — so they may not appear here.</p>
              <button
                onClick={() => setShowTooltip(false)}
                className="mt-2 text-xs text-primary font-medium"
              >
                Got it
              </button>
            </div>
          )}
        </div>
      </div>
      <p className="text-xs text-on-surface-variant/60 mb-4">Based on what Google knows about each business</p>
      <div className="overflow-x-auto -mx-2">
        <table className="w-full text-sm min-w-[500px]">
          <thead>
            <tr className="text-xs text-on-surface-variant">
              <th className="text-left py-2 px-2 font-medium"></th>
              {scorecard.map((c, i) => (
                <th key={i} className={`text-center py-2 px-2 font-semibold ${c.is_owner ? "text-primary" : ""}`}>
                  <div className="truncate max-w-[100px]">{c.is_owner ? "You" : c.name}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              { key: "rating", label: "Rating", render: (c: ScorecardEntry) => c.rating ? `${c.rating}★` : "—" },
              { key: "review_count", label: "Reviews", render: (c: ScorecardEntry) => c.review_count?.toLocaleString() || "0" },
            ].map((row) => (
              <tr key={row.key} className="bg-surface-container-low/40 rounded-lg">
                <td className="py-2.5 px-2 text-on-surface-variant">{row.label}</td>
                {scorecard.map((c, i) => (
                  <td key={i} className={`py-2.5 px-2 text-center font-semibold ${c.is_owner ? "text-primary" : "text-on-surface"}`}>
                    {row.render(c)}
                  </td>
                ))}
              </tr>
            ))}
            {["website", "facebook", "instagram", "tiktok", "foodpanda"].map((field, rowIdx) => (
              <tr key={field} className={rowIdx % 2 === 0 ? "" : "bg-surface-container-low/40"}>
                <td className="py-2.5 px-2 text-on-surface-variant capitalize">
                  {field === "foodpanda" ? "Foodpanda" : field.charAt(0).toUpperCase() + field.slice(1)}
                </td>
                {scorecard.map((c, i) => (
                  <td key={i} className="py-2.5 px-2 text-center">
                    <Check yes={(c as Record<string, unknown>)[field] as boolean} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  4. Social Links                                                    */
/* ------------------------------------------------------------------ */

function SocialIcon({ name, found }: { name: string; found: boolean }) {
  // SVG social icons — colored when found, grey when not
  const grey = "text-on-surface-variant/30";
  switch (name) {
    case "Facebook":
      return (
        <svg viewBox="0 0 24 24" className={`h-6 w-6 ${found ? "" : grey}`} fill={found ? "#1877F2" : "currentColor"}>
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
        </svg>
      );
    case "Instagram":
      return (
        <svg viewBox="0 0 24 24" className={`h-6 w-6 ${found ? "" : grey}`} fill={found ? "#E4405F" : "currentColor"}>
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/>
        </svg>
      );
    case "TikTok":
      return (
        <svg viewBox="0 0 24 24" className={`h-6 w-6 ${found ? "" : grey}`} fill={found ? "#000000" : "currentColor"}>
          <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/>
        </svg>
      );
    default: // Website
      return (
        <Icon name="language" className={`text-2xl ${found ? "text-primary" : grey}`} />
      );
  }
}

export function SocialLinks({ links }: { links: { website: string | null; facebook: string | null; facebook_followers?: string | null; instagram: string | null; instagram_followers?: string | null; tiktok: string | null } }) {
  const items = [
    { name: "Website", url: links.website, followers: null as string | null },
    { name: "Facebook", url: links.facebook, followers: links.facebook_followers || null },
    { name: "Instagram", url: links.instagram, followers: links.instagram_followers || null },
    { name: "TikTok", url: links.tiktok, followers: null },
  ];

  return (
    <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
      <div className="font-headline font-extrabold text-on-surface mb-3">Social Links</div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {items.map((item) => {
          const found = !!item.url;
          const Wrapper = found ? "a" : "div";
          const wrapperProps = found ? { href: item.url!, target: "_blank" as const, rel: "noopener noreferrer" } : {};

          return (
            <Wrapper
              key={item.name}
              {...wrapperProps}
              className={`flex flex-col items-center text-center rounded-lg p-3 transition ${found ? "hover:bg-surface-container-low cursor-pointer" : ""}`}
            >
              <SocialIcon name={item.name} found={found} />
              <div className={`mt-2 text-xs font-semibold ${found ? "text-on-surface" : "text-on-surface-variant/50"}`}>{item.name}</div>
              {found && item.followers ? (
                <div className="text-xs text-on-surface-variant mt-0.5">{item.followers}</div>
              ) : !found ? (
                <div className="text-xs text-on-surface-variant/40 mt-0.5">Not found</div>
              ) : null}
            </Wrapper>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  7. Menu Highlights                                                 */
/* ------------------------------------------------------------------ */

export function MenuHighlights({ items }: { items: { title: string; price?: string }[] }) {
  return (
    <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
      <div className="font-headline font-extrabold text-on-surface mb-3">Menu Highlights</div>
      <p className="text-xs text-on-surface-variant mb-3">Popular items from your Google Maps listing</p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {items.slice(0, 8).map((item, i) => (
          <div key={i} className="rounded-lg bg-surface-container-low p-3 text-center">
            <Icon name="restaurant" className="text-primary/40 text-2xl" />
            <div className="text-sm font-medium text-on-surface mt-1 truncate">{item.title}</div>
            {item.price && <div className="text-xs text-on-surface-variant mt-0.5">{item.price}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  8. Price Positioning                                               */
/* ------------------------------------------------------------------ */

export function PricePositioning({ data }: { data: { distribution: { price: string; percentage: number }[]; total_reported?: number } }) {
  const maxPct = Math.max(...data.distribution.map(d => d.percentage));

  return (
    <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
      <div className="font-headline font-extrabold text-on-surface mb-1">Price Positioning</div>
      {data.total_reported && (
        <p className="text-xs text-on-surface-variant mb-3">Based on {data.total_reported} customer reports</p>
      )}
      <div className="space-y-2">
        {data.distribution.map((d, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-24 text-xs text-on-surface-variant text-right shrink-0">{d.price}</div>
            <div className="flex-1 h-5 rounded-full bg-surface-container-high overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary to-primary-container transition-all"
                style={{ width: `${(d.percentage / maxPct) * 100}%` }}
              />
            </div>
            <div className="w-10 text-xs text-on-surface-variant">{Math.round(d.percentage)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}
