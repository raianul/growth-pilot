import type { Restaurant } from "../hooks/useDiscover";
import RestaurantCard from "./RestaurantCard";

interface NearbySectionProps {
  restaurants: Restaurant[];
  onSelect: (slug: string) => void;
}

export default function NearbySection({ restaurants, onSelect }: NearbySectionProps) {
  if (!restaurants || restaurants.length === 0) return null;

  return (
    <section className="mt-8">
      <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
        Also try nearby
      </h2>
      <div className="flex flex-col gap-3">
        {restaurants.map((restaurant) => (
          <RestaurantCard
            key={restaurant.id}
            restaurant={restaurant}
            onClick={onSelect}
          />
        ))}
      </div>
    </section>
  );
}
