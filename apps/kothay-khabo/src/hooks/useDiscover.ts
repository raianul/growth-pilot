import { useState, useEffect } from "react";
import { discoverSearch } from "../lib/api";

export type Restaurant = {
  id: string; name: string; slug: string; rating: number | null;
  review_count: number; address: string | null; area: string | null;
  lat: number | null; lng: number | null; categories: string | null;
  thumbnail: string | null; price_range: string | null; insight: string | null;
  facebook_url: string | null; instagram_url: string | null;
  menu_highlights: { title: string; price?: string }[];
};

export type DiscoverResult = {
  intent: Record<string, unknown>;
  results: Restaurant[];
  nearby: Restaurant[];
  area: string | null;
};

export function useDiscover(query: string, postcode?: string) {
  const [data, setData] = useState<DiscoverResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    discoverSearch(query, postcode)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [query, postcode]);

  return { data, loading, error };
}
