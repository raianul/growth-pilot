import { useNavigate } from "react-router-dom";

interface Mission {
  id: string;
  title: string;
  channel: string;
  difficulty: "easy" | "medium" | "hard";
  estimated_minutes: number;
  impact_score: number;
  status: string;
}

const CHANNEL_ICONS: Record<string, string> = {
  google_maps: "location_on",
  website: "language",
  youtube: "smart_display",
  reddit: "forum",
  social: "share",
  blog: "article",
  reviews: "star",
  seo: "search",
  default: "flag",
};

const DIFFICULTY_STYLES: Record<
  Mission["difficulty"],
  { bg: string; text: string; label: string }
> = {
  easy: { bg: "bg-green-100", text: "text-green-700", label: "Easy" },
  medium: { bg: "bg-yellow-100", text: "text-yellow-700", label: "Medium" },
  hard: { bg: "bg-red-100", text: "text-red-600", label: "Hard" },
};

interface MissionCardProps {
  mission: Mission;
  rank?: number;
}

export default function MissionCard({ mission, rank }: MissionCardProps) {
  const navigate = useNavigate();
  const icon = CHANNEL_ICONS[mission.channel] ?? CHANNEL_ICONS.default;
  const diff = DIFFICULTY_STYLES[mission.difficulty] ?? DIFFICULTY_STYLES.medium;

  return (
    <button
      onClick={() => navigate(`/missions/${mission.id}`)}
      className="relative w-full text-left bg-surface-container-lowest rounded-xl p-5 shadow-ambient hover:shadow-md transition-shadow group"
    >
      {rank !== undefined && (
        <div className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center z-10">
          {rank}
        </div>
      )}
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
          <span className="material-symbols-outlined text-primary text-xl">
            {icon}
          </span>
        </div>
        <span
          className={`text-xs font-semibold px-2.5 py-1 rounded-full ${diff.bg} ${diff.text}`}
        >
          {diff.label}
        </span>
      </div>

      {/* Title */}
      <h3 className="font-headline font-extrabold text-on-surface text-base leading-snug mb-3 group-hover:text-primary transition-colors">
        {mission.title}
      </h3>

      {/* Meta */}
      <div className="flex items-center gap-4 text-xs text-on-surface-variant">
        <span className="flex items-center gap-1">
          <span className="material-symbols-outlined text-sm">schedule</span>
          {mission.estimated_minutes}m
        </span>
        <span className="flex items-center gap-1">
          <span className="material-symbols-outlined text-sm">bolt</span>
          Impact {mission.impact_score}/10
        </span>
      </div>

      {/* Status chip */}
      {mission.status && mission.status !== "pending" && (
        <div className="mt-3">
          <span className="text-xs px-2 py-0.5 rounded-full bg-surface-container-low text-on-surface-variant capitalize">
            {mission.status.replace("_", " ")}
          </span>
        </div>
      )}
    </button>
  );
}
