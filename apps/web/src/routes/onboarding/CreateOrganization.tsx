import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../../api/client";

const CATEGORIES = [
  "Restaurant & Food",
  "Retail",
  "Health & Beauty",
  "Professional Services",
  "Home Services",
  "Fitness & Wellness",
  "Education",
  "Other",
];

export default function CreateOrganization() {
  const navigate = useNavigate();
  const [businessName, setBusinessName] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!businessName.trim() || !category) return;

    setError(null);
    setLoading(true);
    try {
      await apiFetch("/organizations", {
        method: "POST",
        body: JSON.stringify({
          business_name: businessName.trim(),
          website_url: websiteUrl.trim() || undefined,
          category,
        }),
      });
      navigate("/onboarding/add-outlet");
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to create organization",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="w-full max-w-md">
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

        {/* Step indicator — 4 steps, step 2 active */}
        <div className="flex items-center gap-2 mb-8">
          {[1, 2, 3, 4].map((step) => (
            <div
              key={step}
              className={`h-1.5 rounded-full flex-1 ${
                step <= 2 ? "bg-primary" : "bg-surface-container-high"
              }`}
            />
          ))}
        </div>

        <h1 className="font-headline font-extrabold text-on-surface text-3xl mb-2">
          Tell us about your business
        </h1>
        <p className="text-on-surface-variant mb-8">
          This helps us tailor your growth strategy
        </p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-on-surface mb-1.5">
              Business name
            </label>
            <input
              type="text"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              required
              placeholder="e.g. Joe's Pizza"
              className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-on-surface mb-1.5">
              Website{" "}
              <span className="text-on-surface-variant font-normal">
                (optional)
              </span>
            </label>
            <input
              type="url"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              placeholder="https://yourbusiness.com"
              className="w-full px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-on-surface mb-1.5">
              Category
            </label>
            <div className="grid grid-cols-2 gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategory(cat)}
                  className={`px-3 py-2.5 rounded-xl text-sm font-medium text-left transition-all ${
                    category === cat
                      ? "bg-primary/10 text-primary ring-2 ring-primary"
                      : "bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading || !businessName.trim() || !category}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? "Creating…" : "Continue →"}
          </button>
        </form>

        {/* Trust indicators */}
        <div className="flex items-center justify-center gap-6 mt-10">
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
