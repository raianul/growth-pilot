import { useState, useEffect, type KeyboardEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";

interface Organization {
  id: string;
  business_name: string;
  website_url: string | null;
  category: string | null;
  tone_of_voice: string | null;
  brand_keywords: string[];
}

type Tone = "professional" | "friendly" | "casual" | "bold";

const TONES: Tone[] = ["professional", "friendly", "casual", "bold"];

export default function BrandIdentity() {
  const queryClient = useQueryClient();

  const { data: org, isLoading } = useQuery({
    queryKey: ["organization"],
    queryFn: () => apiFetch<Organization>("/organizations/me"),
  });

  const [businessName, setBusinessName] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [category, setCategory] = useState("");
  const [tone, setTone] = useState<string>("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [kwInput, setKwInput] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (org) {
      setBusinessName(org.business_name ?? "");
      setWebsiteUrl(org.website_url ?? "");
      setCategory(org.category ?? "");
      setTone(org.tone_of_voice ?? "");
      setKeywords(org.brand_keywords ?? []);
    }
  }, [org]);

  const { mutate: save, isPending } = useMutation({
    mutationFn: () =>
      apiFetch("/organizations/me", {
        method: "PATCH",
        body: JSON.stringify({
          business_name: businessName || undefined,
          website_url: websiteUrl || undefined,
          category: category || undefined,
          tone_of_voice: tone || null,
          brand_keywords: keywords,
        }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["organization"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  function addKeyword() {
    const kw = kwInput.trim();
    if (kw && !keywords.includes(kw)) {
      setKeywords([...keywords, kw]);
    }
    setKwInput("");
  }

  function handleKwKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addKeyword();
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="font-headline font-extrabold text-on-surface text-3xl">
          Organization
        </h1>
        <p className="text-on-surface-variant mt-1">
          Manage your organization details and brand voice for AI-generated
          content.
        </p>
      </div>

      {/* Business info */}
      <section className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient space-y-4">
        <h2 className="font-headline font-extrabold text-on-surface text-lg">
          Business Details
        </h2>

        <div>
          <label className="block text-sm font-medium text-on-surface mb-1.5">
            Business name
          </label>
          <input
            type="text"
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
            placeholder="Your business name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-on-surface mb-1.5">
            Website
          </label>
          <input
            type="url"
            value={websiteUrl}
            onChange={(e) => setWebsiteUrl(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
            placeholder="https://yourbusiness.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-on-surface mb-1.5">
            Category
          </label>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
            placeholder="e.g. Restaurant & Food"
          />
        </div>
      </section>

      {/* Tone of voice */}
      <section className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient space-y-4">
        <h2 className="font-headline font-extrabold text-on-surface text-lg">
          Tone of Voice
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {TONES.map((t) => (
            <button
              key={t}
              onClick={() => setTone(t)}
              className={`px-4 py-3 rounded-xl text-sm font-semibold capitalize transition-all ${
                tone === t
                  ? "bg-primary text-white"
                  : "bg-surface-container-low text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      {/* Brand keywords */}
      <section className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient space-y-4">
        <h2 className="font-headline font-extrabold text-on-surface text-lg">
          Brand Keywords
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={kwInput}
            onChange={(e) => setKwInput(e.target.value)}
            onKeyDown={handleKwKeyDown}
            placeholder="Add a keyword and press Enter"
            className="flex-1 px-4 py-3 rounded-xl bg-surface-container-low text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            onClick={addKeyword}
            className="px-4 py-3 rounded-xl bg-surface-container-low text-on-surface-variant hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined text-xl">add</span>
          </button>
        </div>
        {keywords.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw) => (
              <span
                key={kw}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm"
              >
                {kw}
                <button
                  onClick={() =>
                    setKeywords(keywords.filter((k) => k !== kw))
                  }
                  className="hover:opacity-70 transition-opacity"
                  aria-label={`Remove ${kw}`}
                >
                  <span className="material-symbols-outlined text-sm">
                    close
                  </span>
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-on-surface-variant">
            No keywords yet. Add some to guide AI content generation.
          </p>
        )}
      </section>

      {/* Save */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => save()}
          disabled={isPending || !org}
          className="px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {isPending ? "Saving…" : "Save changes"}
        </button>
        {saved && (
          <span className="flex items-center gap-1.5 text-sm text-primary font-medium">
            <span
              className="material-symbols-outlined text-base"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              check_circle
            </span>
            Saved
          </span>
        )}
      </div>
    </div>
  );
}
