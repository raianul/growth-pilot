import { useState, useEffect } from "react";
import type { FormEvent, FocusEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { apiFetch } from "../../api/client";

interface MapsLinkResponse {
  business_name: string;
  rating: number | null;
  reviews: number | null;
  place_id: string | null;
  address: string | null;
  city: string | null;
  category: string | null;
  types: string[];
}

const CATEGORIES = [
  { value: "restaurant", label: "Restaurant & Food", icon: "restaurant" },
  { value: "cafe", label: "Café & Coffee", icon: "local_cafe" },
  { value: "gym", label: "Gym & Fitness", icon: "fitness_center" },
  { value: "salon", label: "Salon & Beauty", icon: "content_cut" },
  { value: "retail", label: "Retail & Shop", icon: "storefront" },
  { value: "bakery", label: "Bakery & Pastry", icon: "cake" },
  { value: "bar", label: "Bar & Nightlife", icon: "local_bar" },
  { value: "other", label: "Other", icon: "category" },
];

export default function SetupBusiness() {
  const navigate = useNavigate();
  const { session, signUp, signIn, isDevMode } = useAuth();
  const isAuthed = isDevMode || !!session;
  const [checkingOnboarding, setCheckingOnboarding] = useState(true);

  // If user is already authed, check if they've already onboarded
  useEffect(() => {
    if (!isAuthed) {
      setCheckingOnboarding(false);
      return;
    }
    apiFetch<{ id: string }[]>("/outlets")
      .then((outlets) => {
        if (outlets && outlets.length > 0) {
          navigate("/dashboard", { replace: true });
        } else {
          setCheckingOnboarding(false);
        }
      })
      .catch(() => {
        setCheckingOnboarding(false);
      });
  }, [isAuthed, navigate]);

  // Show loading while checking onboarding status
  if (checkingOnboarding && isAuthed) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-surface">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Auth state
  const [authMode, setAuthMode] = useState<"signup" | "signin">("signup");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // Maps link state
  const [mapsUrl, setMapsUrl] = useState("");
  const [mapsLoading, setMapsLoading] = useState(false);
  const [mapsResult, setMapsResult] = useState<MapsLinkResponse | null>(null);
  const [mapsError, setMapsError] = useState("");

  // Business state
  const [businessName, setBusinessName] = useState("");
  const [city, setCity] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [category, setCategory] = useState("");
  const [address, setAddress] = useState("");
  const [googlePlaceId, setGooglePlaceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function handleAuth(e: FormEvent) {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);
    try {
      if (authMode === "signup") {
        await signUp(email, password);
      } else {
        await signIn(email, password);
      }
    } catch (err: unknown) {
      setAuthError(
        err instanceof Error ? err.message : "Authentication failed",
      );
    } finally {
      setAuthLoading(false);
    }
  }

  function handleWebsiteBlur(e: FocusEvent<HTMLInputElement>) {
    const val = e.target.value.trim();
    if (val && !val.startsWith("http://") && !val.startsWith("https://")) {
      setWebsiteUrl("https://" + val);
    }
  }

  function handleMapsValidate() {
    const url = mapsUrl.trim();
    if (!url) return;
    setMapsError("");
    setMapsResult(null);
    // Just validate it looks like a Google Maps URL
    if (url.includes("google.com/maps") || url.includes("maps.app.goo.gl") || url.includes("goo.gl/maps")) {
      setMapsResult({ business_name: "Link saved", rating: null, reviews: null, place_id: null, address: null, city: null, category: null, types: [] });
    } else {
      setMapsError("Please paste a Google Maps link (e.g. https://maps.app.goo.gl/...)");
    }
  }

  function validate() {
    const newErrors: Record<string, string> = {};
    if (!businessName.trim())
      newErrors.businessName = "Business name is required";
    if (!city.trim()) newErrors.city = "City is required";
    if (!category) newErrors.category = "Please select a category";
    return newErrors;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setErrors({});
    setLoading(true);
    try {
      // Create org — if it already exists, update it instead
      try {
        await apiFetch("/organizations", {
          method: "POST",
          body: JSON.stringify({
            business_name: businessName.trim(),
            website_url: websiteUrl.trim() || undefined,
            category,
          }),
        });
      } catch {
        // Org already exists — update it
        await apiFetch("/organizations/me", {
          method: "PATCH",
          body: JSON.stringify({
            business_name: businessName.trim(),
            website_url: websiteUrl.trim() || undefined,
            category,
          }),
        });
      }

      await apiFetch("/outlets", {
        method: "POST",
        body: JSON.stringify({
          outlet_name: `${businessName.trim()} — ${city.trim()}`,
          city: city.trim(),
          address: address.trim() || undefined,
          google_place_id: googlePlaceId || undefined,
          maps_url: mapsUrl.trim() || undefined,
        }),
      });

      navigate("/onboarding/brand-voice");
    } catch (err: unknown) {
      setErrors({
        form: "Something went wrong. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-primary-container flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-xl">
              rocket_launch
            </span>
          </div>
          <span className="font-headline font-extrabold text-on-surface text-2xl">
            GrowthPilot
          </span>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-2">
          <div className="h-1.5 rounded-full flex-1 bg-primary" />
          <div className="h-1.5 rounded-full flex-1 bg-surface-container-high" />
        </div>
        <div className="flex justify-between mb-8">
          <span className="text-xs font-medium text-primary">
            {isAuthed ? "About Your Business" : "Create Account"}
          </span>
          <span className="text-xs text-on-surface-variant">Brand Voice</span>
        </div>

        {/* === Auth form (shown when not logged in) === */}
        {!isAuthed && (
          <>
            <h1 className="font-headline font-extrabold text-on-surface text-3xl mb-2">
              {authMode === "signup" ? "Create your account" : "Welcome back"}
            </h1>
            <p className="text-on-surface-variant mb-8">
              {authMode === "signup"
                ? "Get started with GrowthPilot in minutes"
                : "Sign in to continue"}
            </p>

            <form onSubmit={handleAuth} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-on-surface mb-1.5">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="you@example.com"
                  className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-on-surface mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  placeholder="Min. 6 characters"
                  className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              {authError && (
                <p className="text-sm text-red-500">{authError}</p>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {authLoading
                  ? "Loading…"
                  : authMode === "signup"
                    ? "Create account"
                    : "Sign in"}
              </button>

              <p className="text-center text-sm text-on-surface-variant">
                {authMode === "signup"
                  ? "Already have an account? "
                  : "Need an account? "}
                <button
                  type="button"
                  onClick={() =>
                    setAuthMode(authMode === "signup" ? "signin" : "signup")
                  }
                  className="text-primary font-medium hover:underline"
                >
                  {authMode === "signup" ? "Sign in" : "Sign up"}
                </button>
              </p>
            </form>
          </>
        )}

        {/* === Business form (shown after auth) === */}
        {isAuthed && (
          <>
            <h1 className="font-headline font-extrabold text-on-surface text-3xl mb-2">
              About your business
            </h1>
            <p className="text-on-surface-variant mb-8">
              Tell us the basics — we'll build your growth strategy around them.
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Business name */}
              <div>
                <label className="block text-sm font-medium text-on-surface mb-1.5">
                  Business name
                </label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => {
                    setBusinessName(e.target.value);
                    if (errors.businessName)
                      setErrors((prev) => ({ ...prev, businessName: "" }));
                  }}
                  placeholder="e.g. Joe's Pizza"
                  className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
                {errors.businessName && (
                  <p className="mt-1.5 text-xs text-red-500">
                    {errors.businessName}
                  </p>
                )}
              </div>

              {/* City */}
              <div>
                <label className="block text-sm font-medium text-on-surface mb-1.5">
                  City
                </label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => {
                    setCity(e.target.value);
                    if (errors.city)
                      setErrors((prev) => ({ ...prev, city: "" }));
                  }}
                  placeholder="e.g. Berlin"
                  className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
                {errors.city && (
                  <p className="mt-1.5 text-xs text-red-500">{errors.city}</p>
                )}
              </div>

              {/* Website */}
              <div>
                <label className="block text-sm font-medium text-on-surface mb-1.5">
                  Website{" "}
                  <span className="text-on-surface-variant font-normal">
                    (optional)
                  </span>
                </label>
                <input
                  type="text"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  onBlur={handleWebsiteBlur}
                  placeholder="yourbusiness.com"
                  className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-on-surface mb-1.5">
                  Category
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {CATEGORIES.map((cat) => (
                    <button
                      key={cat.value}
                      type="button"
                      onClick={() => {
                        setCategory(cat.value);
                        if (errors.category)
                          setErrors((prev) => ({ ...prev, category: "" }));
                      }}
                      className={`flex items-center gap-2.5 px-3 py-3 rounded-xl text-sm font-medium text-left transition-all ${
                        category === cat.value
                          ? "bg-primary/10 text-primary ring-2 ring-primary"
                          : "bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                      }`}
                    >
                      <span
                        className="material-symbols-outlined text-lg shrink-0"
                        style={{
                          fontVariationSettings:
                            category === cat.value
                              ? "'FILL' 1"
                              : "'FILL' 0",
                        }}
                      >
                        {cat.icon}
                      </span>
                      {cat.label}
                    </button>
                  ))}
                </div>
                {errors.category && (
                  <p className="mt-1.5 text-xs text-red-500">
                    {errors.category}
                  </p>
                )}
              </div>

              {/* Address */}
              <div>
                <label className="block text-sm font-medium text-on-surface mb-1.5">
                  Address{" "}
                  <span className="text-on-surface-variant font-normal">
                    (optional)
                  </span>
                </label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="e.g. 123 Main St"
                  className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
                <p className="mt-1.5 text-xs text-on-surface-variant">
                  Helps us find you on Google Maps
                </p>
              </div>

              {/* Google Maps link */}
              <div>
                <label className="block text-sm font-medium text-on-surface mb-1.5">
                  Google Maps link{" "}
                  <span className="text-on-surface-variant font-normal">
                    (paste your business link)
                  </span>
                </label>
                <input
                  type="text"
                  value={mapsUrl}
                  onChange={(e) => setMapsUrl(e.target.value)}
                  placeholder="https://maps.app.goo.gl/..."
                  className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
                <p className="mt-1.5 text-xs text-on-surface-variant">
                  We use this to track your Google Maps ranking and reviews
                </p>
              </div>

              {errors.form && (
                <p className="text-sm text-red-500">{errors.form}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? "Setting up…" : "Continue →"}
              </button>
            </form>
          </>
        )}

        {/* Trust indicators */}
        <div className="flex items-center justify-center gap-6 mt-10 flex-wrap">
          {[
            "No credit card required",
            "Setup in 2 minutes",
            "Cancel anytime",
          ].map((t) => (
            <span
              key={t}
              className="flex items-center gap-1 text-xs text-on-surface-variant"
            >
              <span
                className="material-symbols-outlined text-primary text-sm"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                check_circle
              </span>
              {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
