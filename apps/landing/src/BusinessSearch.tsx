import { useEffect, useRef, useState } from "react";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/v1";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return (
    <span className={`material-symbols-outlined ${className}`}>{name}</span>
  );
}

type SearchResult = {
  id: string;
  business_name: string;
  slug: string | null;
  google_place_id: string;
  rating: number | null;
  review_count: number;
  address: string | null;
  categories: string | null;
  postcode: string | null;
  thumbnail: string | null;
};

type StartAuditPayload = { type: "place_id"; google_place_id: string; business_name: string; slug: string | null };

function HighlightMatch({ text, query }: { text: string; query: string }) {
  if (!query || query.length < 2) return <>{text}</>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-primary/15 text-on-surface rounded-sm px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

export default function BusinessSearch({
  onStartAudit,
  variant = "hero",
}: {
  onStartAudit: (payload: StartAuditPayload) => void;
  variant?: "hero" | "page";
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [noResults, setNoResults] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
        setActiveIndex(-1);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Debounced search
  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setShowDropdown(false);
      setNoResults(false);
      setActiveIndex(-1);
      return;
    }

    setLoading(true);
    setNoResults(false);
    clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/businesses/search?q=${encodeURIComponent(query)}&limit=5`);
        const data = await res.json();
        setResults(data.results || []);
        setShowDropdown(true);
        setNoResults((data.results || []).length === 0);
        setActiveIndex(-1);
      } catch {
        setResults([]);
        setNoResults(true);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(debounceRef.current);
  }, [query]);

  function handleSelectResult(r: SearchResult) {
    setShowDropdown(false);
    setActiveIndex(-1);
    setQuery(r.business_name);
    onStartAudit({ type: "place_id", google_place_id: r.google_place_id, business_name: r.business_name, slug: r.slug });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showDropdown || results.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      handleSelectResult(results[activeIndex]);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      setActiveIndex(-1);
      inputRef.current?.blur();
    }
  }

  const isHero = variant === "hero";
  const inputBg = isHero ? "bg-white/95" : "bg-surface-container-lowest";
  const inputText = "text-on-surface placeholder:text-on-surface-variant/60";
  const inputRing = isHero ? "focus:ring-2 focus:ring-white/40" : "focus:ring-2 focus:ring-primary/20";

  return (
    <div ref={wrapperRef} className="relative">
      <div className="relative">
        <Icon
          name="search"
          className={`absolute left-3 top-1/2 -translate-y-1/2 text-xl ${isHero ? "text-on-surface-variant/50" : "text-on-surface-variant/40"}`}
        />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={showDropdown}
          aria-autocomplete="list"
          aria-controls="search-listbox"
          aria-activedescendant={activeIndex >= 0 ? `search-option-${activeIndex}` : undefined}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { if (results.length > 0 || noResults) setShowDropdown(true); }}
          onKeyDown={handleKeyDown}
          placeholder="Search your restaurant name..."
          autoComplete="off"
          className={`w-full rounded-lg ${inputBg} pl-10 pr-10 py-3.5 ${inputText} shadow-ambient focus:outline-none ${inputRing}`}
        />
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          </div>
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div
          id="search-listbox"
          role="listbox"
          className="absolute left-0 right-0 top-full mt-1 z-50 rounded-lg bg-surface-container-lowest shadow-ambient overflow-hidden"
        >
          {results.length > 0 ? (
            results.map((r, idx) => (
              <button
                key={r.google_place_id}
                id={`search-option-${idx}`}
                role="option"
                aria-selected={activeIndex === idx}
                onClick={() => handleSelectResult(r)}
                onMouseEnter={() => setActiveIndex(idx)}
                className={`w-full flex items-center gap-3 px-4 py-3.5 text-left transition ${
                  activeIndex === idx ? "bg-surface-container-low" : "hover:bg-surface-container-low"
                }`}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Icon name="restaurant" className="text-primary text-base" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-on-surface truncate">
                    <HighlightMatch text={r.business_name} query={query} />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-on-surface-variant">
                    {r.rating && <span>{r.rating}★</span>}
                    {r.review_count > 0 && <span>· {r.review_count.toLocaleString()} reviews</span>}
                  </div>
                  {r.address && (
                    <div className="text-xs text-on-surface-variant/60 truncate mt-0.5">
                      {r.address}
                    </div>
                  )}
                </div>
              </button>
            ))
          ) : noResults ? (
            <div className="px-4 py-5 text-center">
              <p className="text-sm text-on-surface-variant">No restaurants found for "{query}"</p>
              <p className="mt-1 text-xs text-on-surface-variant/50">Try a different spelling or shorter name</p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export type { StartAuditPayload };
