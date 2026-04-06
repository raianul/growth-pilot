import { useState } from "react";
import { useDiscover } from "../hooks/useDiscover";
import SearchInput from "../components/SearchInput";
import RestaurantCard from "../components/RestaurantCard";
import NearbySection from "../components/NearbySection";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

interface ResultsPageProps {
  query: string;
  postcode?: string;
  onSelectRestaurant: (slug: string) => void;
  onBack: () => void;
  onNewSearch: (query: string, postcode?: string) => void;
}

export default function ResultsPage({
  query,
  postcode,
  onSelectRestaurant,
  onBack,
  onNewSearch,
}: ResultsPageProps) {
  const { data, loading, error } = useDiscover(query, postcode);
  const [showMap, setShowMap] = useState(false);

  return (
    <div className="min-h-screen bg-surface font-body">
      {/* Gradient header */}
      <header className="sticky top-0 z-10 bg-gradient-to-r from-primary to-primary-container px-4 pt-safe-top pb-4 shadow-ambient">
        <div className="flex items-center gap-3 mb-3">
          <button
            onClick={onBack}
            aria-label="Go back"
            className="shrink-0 flex items-center justify-center w-9 h-9 rounded-lg bg-white/10 text-white backdrop-blur-sm hover:bg-white/20 transition"
          >
            <Icon name="arrow_back" className="text-xl" />
          </button>
          <div className="flex-1">
            <SearchInput onSearch={(q) => onNewSearch(q, postcode)} />
          </div>
        </div>
      </header>

      <main className="px-4 pb-10 pt-6 max-w-xl mx-auto">
        {/* Loading state */}
        {loading && (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
            <p className="text-on-surface-variant font-body text-sm">Finding restaurants for you...</p>
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="rounded-lg bg-red-50 px-4 py-4 text-sm text-red-700 font-body">
            <div className="flex items-center gap-2">
              <Icon name="error" className="text-base text-red-500" />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Results */}
        {!loading && !error && data && (
          <>
            {/* Intent summary */}
            {data.area && (
              <p className="text-sm text-on-surface-variant font-body mb-4">
                Showing results in{" "}
                <span className="font-semibold text-on-surface">{data.area}</span>
              </p>
            )}

            {/* Map toggle */}
            <div className="flex justify-end mb-4">
              <button
                onClick={() => setShowMap((v) => !v)}
                className="flex items-center gap-1.5 rounded-lg bg-surface-container-low px-3 py-2 text-sm font-body text-on-surface hover:bg-surface-container-high transition"
              >
                <Icon name={showMap ? "list" : "map"} className="text-base text-primary" />
                {showMap ? "Show list" : "Show map"}
              </button>
            </div>

            {/* Map placeholder */}
            {showMap && (
              <div className="rounded-lg bg-surface-container-high h-48 flex items-center justify-center mb-6">
                <p className="text-sm text-on-surface-variant font-body">Map view coming soon</p>
              </div>
            )}

            {/* Results list */}
            {!showMap && (
              <>
                {data.results.length === 0 ? (
                  <div className="flex flex-col items-center gap-3 py-16 text-center">
                    <Icon name="search_off" className="text-4xl text-on-surface-variant/40" />
                    <p className="text-on-surface-variant font-body text-sm">No restaurants found</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    {data.results.map((restaurant, index) => (
                      <RestaurantCard
                        key={restaurant.id}
                        restaurant={restaurant}
                        rank={index + 1}
                        onClick={onSelectRestaurant}
                      />
                    ))}
                  </div>
                )}

                <NearbySection
                  restaurants={data.nearby}
                  onSelect={onSelectRestaurant}
                />
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
