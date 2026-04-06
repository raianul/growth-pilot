import { useEffect, useState } from "react";
import { getRestaurant } from "../lib/api";
import ReviewModal from "../components/ReviewModal";

function Icon({ name, className = "", fill = false }: { name: string; className?: string; fill?: boolean }) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={fill ? ({ fontVariationSettings: "'FILL' 1" } as React.CSSProperties) : undefined}
    >
      {name}
    </span>
  );
}

interface ReviewStats {
  total: number;
  food_good_pct: number;
  environment_good_pct: number;
  recommend_pct: number;
}

interface ReviewAnalysis {
  summary: string | null;
  top_praised: string[];
  top_complaints: string[];
  sentiment: string | null;
}

interface Restaurant {
  id: string;
  name: string;
  slug: string;
  rating: number | null;
  review_count: number;
  address: string | null;
  area: string | null;
  lat: number | null;
  lng: number | null;
  categories: string | null;
  thumbnail: string | null;
  phone: string | null;
  website_url: string | null;
  facebook_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  menu_highlights: string[] | null;
  price_details: string | null;
  review_analysis: ReviewAnalysis | null;
  review_stats: ReviewStats | null;
}

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className="material-symbols-outlined text-lg text-amber-400"
          style={
            n <= Math.round(rating)
              ? ({ fontVariationSettings: "'FILL' 1" } as React.CSSProperties)
              : undefined
          }
        >
          star
        </span>
      ))}
    </span>
  );
}

function StatPill({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="font-headline font-extrabold text-2xl text-primary">{value}%</span>
      <span className="font-body text-xs text-on-surface-variant text-center leading-tight">{label}</span>
    </div>
  );
}

interface RestaurantPageProps {
  slug: string;
  onBack: () => void;
}

export default function RestaurantPage({ slug, onBack }: RestaurantPageProps) {
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [showReview, setShowReview] = useState(false);

  useEffect(() => {
    setLoading(true);
    setNotFound(false);
    getRestaurant(slug)
      .then((data) => setRestaurant(data))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <div className="min-h-screen bg-surface">
      {/* Gradient header */}
      <header
        className="sticky top-0 z-40 flex items-center gap-3 px-4 py-3"
        style={{ background: "linear-gradient(135deg, #0037b0, #1d4ed8)" }}
      >
        <button
          onClick={onBack}
          className="w-9 h-9 rounded-lg flex items-center justify-center text-white/80 hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Go back"
        >
          <Icon name="arrow_back" className="text-xl" />
        </button>
        <h1 className="font-headline font-extrabold text-white text-base flex-1 truncate">
          {restaurant?.name ?? (loading ? "" : "Restaurant")}
        </h1>
      </header>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center items-center py-24">
          <span className="material-symbols-outlined text-4xl text-primary animate-spin">progress_activity</span>
        </div>
      )}

      {/* Not found */}
      {!loading && notFound && (
        <div className="flex flex-col items-center gap-4 py-24 px-6 text-center">
          <Icon name="search_off" className="text-5xl text-on-surface-variant/40" />
          <p className="font-headline font-extrabold text-xl text-on-surface">Restaurant not found</p>
          <p className="font-body text-sm text-on-surface-variant">
            This restaurant may have been removed or the link is incorrect.
          </p>
          <button
            onClick={onBack}
            className="mt-2 px-6 py-3 rounded-lg font-headline font-extrabold text-white text-sm"
            style={{ background: "linear-gradient(135deg, #0037b0, #1d4ed8)" }}
          >
            Go back
          </button>
        </div>
      )}

      {/* Content */}
      {!loading && restaurant && (
        <main className="px-4 py-5 space-y-4 max-w-lg mx-auto pb-10">

          {/* 1. Hero card */}
          <section className="bg-surface-container-lowest rounded-lg shadow-ambient p-5">
            {restaurant.thumbnail && (
              <img
                src={restaurant.thumbnail}
                alt={restaurant.name}
                className="w-full h-44 object-cover rounded-lg mb-4"
              />
            )}
            {!restaurant.thumbnail && (
              <div className="w-full h-44 rounded-lg bg-surface-container-high flex items-center justify-center mb-4">
                <Icon name="restaurant" className="text-5xl text-on-surface-variant/30" />
              </div>
            )}

            <h2 className="font-headline font-extrabold text-xl text-on-surface leading-tight">
              {restaurant.name}
            </h2>

            {restaurant.categories && (
              <p className="text-sm text-on-surface-variant font-body mt-0.5">{restaurant.categories}</p>
            )}

            {restaurant.rating !== null && (
              <div className="flex items-center gap-2 mt-2">
                <StarRating rating={restaurant.rating} />
                <span className="font-body text-sm font-semibold text-on-surface">
                  {restaurant.rating.toFixed(1)}
                </span>
                {restaurant.review_count > 0 && (
                  <span className="font-body text-xs text-on-surface-variant">
                    ({restaurant.review_count} reviews)
                  </span>
                )}
              </div>
            )}

            {restaurant.address && (
              <div className="flex items-start gap-1.5 mt-3">
                <Icon name="location_on" className="text-base text-primary mt-0.5 shrink-0" />
                <p className="font-body text-sm text-on-surface-variant">{restaurant.address}</p>
              </div>
            )}

            {/* Quick actions */}
            {(restaurant.phone || (restaurant.lat && restaurant.lng)) && (
              <div className="flex gap-2 mt-4">
                {restaurant.phone && (
                  <a
                    href={`tel:${restaurant.phone}`}
                    className="flex items-center gap-1.5 bg-surface-container-low rounded-lg px-3 py-2 font-body text-sm font-semibold text-on-surface"
                  >
                    <Icon name="call" className="text-base text-primary" />
                    Call
                  </a>
                )}
                {restaurant.lat && restaurant.lng && (
                  <a
                    href={`https://www.google.com/maps/dir/?api=1&destination=${restaurant.lat},${restaurant.lng}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 bg-surface-container-low rounded-lg px-3 py-2 font-body text-sm font-semibold text-on-surface"
                  >
                    <Icon name="directions" className="text-base text-primary" />
                    Directions
                  </a>
                )}
              </div>
            )}
          </section>

          {/* 2. KothayKhabo Reviews */}
          {restaurant.review_stats && (
            <section className="bg-surface-container-lowest rounded-lg shadow-ambient p-5">
              <h3 className="font-headline font-extrabold text-base text-on-surface mb-4">
                KothayKhabo Reviews
              </h3>
              <div className="grid grid-cols-3 gap-3">
                <StatPill value={restaurant.review_stats.food_good_pct} label="Good food" />
                <StatPill value={restaurant.review_stats.environment_good_pct} label="Good environment" />
                <StatPill value={restaurant.review_stats.recommend_pct} label="Would recommend" />
              </div>
              <p className="font-body text-xs text-on-surface-variant text-center mt-3">
                Based on {restaurant.review_stats.total} {restaurant.review_stats.total === 1 ? "review" : "reviews"}
              </p>
            </section>
          )}

          {/* 3. What customers say */}
          {(restaurant.review_analysis?.top_praised?.length || restaurant.review_analysis?.top_complaints?.length) ? (
            <section className="bg-surface-container-lowest rounded-lg shadow-ambient p-5">
              <h3 className="font-headline font-extrabold text-base text-on-surface mb-4">
                What customers say
              </h3>

              {!!restaurant.review_analysis?.top_praised?.length && (
                <div className="mb-4">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Icon name="thumb_up" className="text-sm text-green-600" fill />
                    <span className="font-body text-sm font-semibold text-green-700">Love</span>
                  </div>
                  <ul className="space-y-1.5">
                    {restaurant.review_analysis.top_praised.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 font-body text-sm text-on-surface-variant">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!!restaurant.review_analysis?.top_complaints?.length && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Icon name="thumb_down" className="text-sm text-red-500" fill />
                    <span className="font-body text-sm font-semibold text-red-600">Could improve</span>
                  </div>
                  <ul className="space-y-1.5">
                    {restaurant.review_analysis.top_complaints.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 font-body text-sm text-on-surface-variant">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          ) : null}

          {/* 4. Popular items */}
          {restaurant.menu_highlights && restaurant.menu_highlights.length > 0 && (
            <section className="bg-surface-container-lowest rounded-lg shadow-ambient p-5">
              <h3 className="font-headline font-extrabold text-base text-on-surface mb-4">
                Popular items
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {restaurant.menu_highlights.map((item, i) => (
                  <div
                    key={i}
                    className="bg-surface-container-low rounded-lg px-3 py-2.5 font-body text-sm text-on-surface"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 5. Review CTA */}
          <button
            onClick={() => setShowReview(true)}
            className="w-full py-4 rounded-lg font-headline font-extrabold text-white text-base shadow-ambient"
            style={{ background: "linear-gradient(135deg, #0037b0, #1d4ed8)" }}
          >
            Rate this restaurant (10 secs)
          </button>

        </main>
      )}

      {showReview && restaurant && (
        <ReviewModal
          businessId={restaurant.id}
          onClose={() => setShowReview(false)}
        />
      )}
    </div>
  );
}
