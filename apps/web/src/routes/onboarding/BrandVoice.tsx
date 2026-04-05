import { useState, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";

interface Outlet {
  id: string;
  outlet_name: string;
}

type Tone = "professional" | "friendly" | "casual" | "bold";

interface ToneCard {
  value: Tone;
  label: string;
  description: string;
  icon: string;
}

const TONE_CARDS: ToneCard[] = [
  {
    value: "professional",
    label: "Professional",
    description:
      "Authoritative and polished. Ideal for B2B, legal, finance, and service businesses that want to project expertise and credibility.",
    icon: "business_center",
  },
  {
    value: "friendly",
    label: "Friendly",
    description:
      "Warm and approachable. Builds genuine community trust — perfect for local shops, family restaurants, and neighborhood services.",
    icon: "favorite",
  },
  {
    value: "casual",
    label: "Casual",
    description:
      "Relaxed and conversational. Feels human and relatable — great for cafés, studios, and brands with a young, social-first audience.",
    icon: "emoji_emotions",
  },
  {
    value: "bold",
    label: "Bold",
    description:
      "Direct and energetic. Commands attention and drives action — ideal for gyms, bars, and brands that want to stand out.",
    icon: "bolt",
  },
];

export default function BrandVoice() {
  const navigate = useNavigate();
  const [tone, setTone] = useState<Tone | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [kwInput, setKwInput] = useState("");

  const { mutate: save, isPending } = useMutation({
    mutationFn: async () => {
      // Save tone + keywords to organization
      await apiFetch("/organizations/me", {
        method: "PATCH",
        body: JSON.stringify({
          tone_of_voice: tone,
          brand_keywords: keywords,
        }),
      });

      // Trigger audit on first outlet
      const outlets = await apiFetch<Outlet[]>("/outlets");
      const firstOutletId = outlets?.[0]?.id;
      if (firstOutletId) {
        await apiFetch(`/outlets/${firstOutletId}/audit`, { method: "POST" });
      }
    },
    onSuccess: () => navigate("/dashboard"),
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

  function removeKeyword(kw: string) {
    setKeywords(keywords.filter((k) => k !== kw));
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
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

        {/* Step indicator — 2 steps, step 2 active */}
        <div className="flex items-center gap-2 mb-2">
          <div className="h-1.5 rounded-full flex-1 bg-primary" />
          <div className="h-1.5 rounded-full flex-1 bg-primary" />
        </div>
        <div className="flex justify-between mb-8">
          <span className="text-xs text-on-surface-variant">About Your Business</span>
          <span className="text-xs font-medium text-primary">Brand Voice</span>
        </div>

        <h1 className="font-headline font-extrabold text-on-surface text-3xl mb-2">
          Your brand voice
        </h1>
        <p className="text-on-surface-variant mb-8">
          Choose the tone that best represents your business — you can change this anytime.
        </p>

        {/* Tone grid */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          {TONE_CARDS.map((card) => (
            <button
              key={card.value}
              onClick={() => setTone(card.value)}
              className={`p-5 rounded-xl text-left transition-all ${
                tone === card.value
                  ? "bg-primary/10 ring-2 ring-primary"
                  : "bg-surface-container-lowest hover:bg-surface-container-low shadow-ambient"
              }`}
            >
              <span
                className={`material-symbols-outlined text-2xl mb-3 block ${
                  tone === card.value
                    ? "text-primary"
                    : "text-on-surface-variant"
                }`}
                style={{
                  fontVariationSettings:
                    tone === card.value ? "'FILL' 1" : "'FILL' 0",
                }}
              >
                {card.icon}
              </span>
              <h3
                className={`font-headline font-extrabold text-base mb-1 ${
                  tone === card.value ? "text-primary" : "text-on-surface"
                }`}
              >
                {card.label}
              </h3>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                {card.description}
              </p>
            </button>
          ))}
        </div>

        {/* Keywords */}
        <div className="mb-8">
          <label className="block text-sm font-medium text-on-surface mb-1.5">
            Brand keywords{" "}
            <span className="text-on-surface-variant font-normal">
              (optional)
            </span>
          </label>
          <p className="text-xs text-on-surface-variant mb-2.5">
            Words that describe what makes you unique — e.g. "organic", "family-owned", "fast delivery"
          </p>
          <div className="flex gap-3 mb-3">
            <input
              type="text"
              value={kwInput}
              onChange={(e) => setKwInput(e.target.value)}
              onKeyDown={handleKwKeyDown}
              placeholder="Type a keyword and press Enter or comma"
              className="flex-1 px-4 py-3 rounded-xl bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            <button
              onClick={addKeyword}
              className="px-4 py-3 rounded-xl bg-surface-container-low text-on-surface-variant hover:text-on-surface transition-colors"
            >
              <span className="material-symbols-outlined text-xl">add</span>
            </button>
          </div>
          {keywords.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {keywords.map((kw) => (
                <span
                  key={kw}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm"
                >
                  {kw}
                  <button
                    onClick={() => removeKeyword(kw)}
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
          )}
        </div>

        <button
          onClick={() => save()}
          disabled={!tone || isPending}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {isPending ? "Launching your plan…" : "Launch my growth plan →"}
        </button>

        <div className="mt-5 text-center">
          <button
            type="button"
            onClick={() => navigate("/onboarding")}
            className="text-sm text-on-surface-variant hover:text-on-surface transition-colors"
          >
            ← Back
          </button>
        </div>
      </div>
    </div>
  );
}
