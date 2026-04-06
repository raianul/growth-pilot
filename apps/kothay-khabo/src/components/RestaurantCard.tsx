import type { Restaurant } from "../hooks/useDiscover";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

interface RestaurantCardProps {
  restaurant: Restaurant;
  rank?: number;
  onClick: (slug: string) => void;
}

export default function RestaurantCard({ restaurant, rank, onClick }: RestaurantCardProps) {
  const { name, slug, rating, review_count, price_range, insight, area, thumbnail, categories } = restaurant;

  return (
    <button
      onClick={() => onClick(slug)}
      className="w-full text-left bg-surface-container-lowest rounded-lg shadow-ambient p-4 flex gap-4 active:scale-[0.98] transition-transform"
    >
      {/* Thumbnail */}
      <div className="relative shrink-0">
        {thumbnail ? (
          <img
            src={thumbnail}
            alt={name}
            className="w-20 h-20 rounded-lg object-cover"
          />
        ) : (
          <div className="w-20 h-20 rounded-lg bg-surface-container-high flex items-center justify-center">
            <Icon name="restaurant" className="text-3xl text-on-surface-variant/40" />
          </div>
        )}
        {rank !== undefined && (
          <span className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-primary text-white text-xs font-bold font-headline flex items-center justify-center shadow-ambient">
            {rank}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <h3 className="font-headline font-extrabold text-on-surface text-base leading-tight truncate">
          {name}
        </h3>

        {categories && (
          <p className="text-xs text-on-surface-variant mt-0.5 truncate">{categories}</p>
        )}

        {/* Rating + reviews + price */}
        <div className="flex items-center gap-2 mt-1.5">
          {rating !== null && (
            <span className="flex items-center gap-0.5 text-sm font-body text-on-surface">
              <Icon name="star" className="text-sm text-amber-400" style={{ fontVariationSettings: "'FILL' 1" } as React.CSSProperties} />
              <span className="font-semibold">{rating.toFixed(1)}</span>
              {review_count > 0 && (
                <span className="text-on-surface-variant text-xs">({review_count})</span>
              )}
            </span>
          )}
          {price_range && (
            <span className="text-xs text-on-surface-variant font-body">{price_range}</span>
          )}
        </div>

        {/* Insight */}
        {insight && (
          <p className="mt-1.5 text-xs text-on-surface-variant font-body italic line-clamp-2 leading-relaxed">
            "{insight}"
          </p>
        )}

        {/* Area */}
        {area && (
          <div className="flex items-center gap-1 mt-1.5">
            <Icon name="location_on" className="text-sm text-primary" />
            <span className="text-xs text-on-surface-variant font-body truncate">{area}</span>
          </div>
        )}
      </div>
    </button>
  );
}
