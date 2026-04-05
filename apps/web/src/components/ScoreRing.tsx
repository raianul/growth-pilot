interface ScoreRingProps {
  score: number;
  delta?: number | null;
  size?: number;
  strokeWidth?: number;
  label?: string;
}

export default function ScoreRing({
  score,
  delta,
  size = 120,
  strokeWidth = 10,
  label,
}: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.max(0, Math.min(100, score));
  const offset = circumference - (clampedScore / 100) * circumference;

  const color =
    clampedScore >= 70
      ? "#0037b0"
      : clampedScore >= 40
        ? "#1d4ed8"
        : "#6b7280";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="-rotate-90"
          aria-hidden="true"
        >
          {/* Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#e6e8ea"
            strokeWidth={strokeWidth}
          />
          {/* Progress */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-headline font-extrabold text-2xl text-on-surface leading-none">
            {clampedScore}
          </span>
          {delta != null && (
            <span
              className={`text-xs font-medium mt-0.5 ${
                delta >= 0 ? "text-primary" : "text-red-500"
              }`}
            >
              {delta >= 0 ? "+" : ""}
              {delta}
            </span>
          )}
        </div>
      </div>
      {label && (
        <span className="text-sm font-medium text-on-surface-variant">
          {label}
        </span>
      )}
    </div>
  );
}
