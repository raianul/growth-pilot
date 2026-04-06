const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/v1/discover";

export async function discoverSearch(query: string, postcode?: string) {
  const params = new URLSearchParams({ q: query });
  if (postcode) params.set("postcode", postcode);
  const res = await fetch(`${API_BASE}/search?${params}`);
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function getRestaurant(slug: string) {
  const res = await fetch(`${API_BASE}/restaurant/${slug}`);
  if (!res.ok) throw new Error("Not found");
  return res.json();
}

export async function phoneAuth(phone: string, name?: string) {
  const res = await fetch(`${API_BASE}/auth/phone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, name }),
  });
  if (!res.ok) throw new Error("Auth failed");
  return res.json();
}

export async function submitReview(userId: string, businessId: string, food: boolean, env: boolean, recommend: boolean) {
  const res = await fetch(`${API_BASE}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, business_id: businessId, food_good: food, environment_good: env, would_recommend: recommend }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Review failed");
  }
  return res.json();
}
