import { useState, useRef } from "react";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

const SUGGESTIONS = [
  "Best burger near me",
  "Biryani under 500 BDT",
  "Quiet café for two",
  "Family dinner in Uttara",
  "ভালো বিরিয়ানি কোথায় পাবো?",
];

export default function SearchInput({ onSearch }: { onSearch: (query: string) => void }) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim().length < 2) return;
    onSearch(query.trim());
  }

  function handleSuggestion(s: string) {
    setQuery(s);
    onSearch(s);
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="relative">
        <Icon name="search" className="absolute left-4 top-1/2 -translate-y-1/2 text-xl text-on-surface-variant/50" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 200)}
          placeholder="What are you craving?"
          className="w-full rounded-lg bg-surface-container-lowest pl-12 pr-12 py-4 text-on-surface placeholder:text-on-surface-variant/50 shadow-ambient focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
        {query && (
          <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-full bg-primary text-white">
            <Icon name="arrow_forward" className="text-base" />
          </button>
        )}
      </form>
      {focused && !query && (
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button key={s} onMouseDown={() => handleSuggestion(s)} className="rounded-full bg-surface-container-low px-3 py-1.5 text-xs text-on-surface-variant hover:bg-surface-container-high transition">
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
