import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { useUIStore } from "../store/uiStore";

interface Outlet {
  id: string;
  outlet_name: string;
  city: string;
}

interface OutletSwitcherProps {
  collapsed?: boolean;
}

export default function OutletSwitcher({ collapsed = false }: OutletSwitcherProps) {
  const { selectedOutletId, setSelectedOutlet } = useUIStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const { data: outlets } = useQuery({
    queryKey: ["outlets"],
    queryFn: () => apiFetch<Outlet[]>("/outlets"),
  });

  // Auto-select first outlet if none selected
  useEffect(() => {
    if (outlets && outlets.length > 0 && !selectedOutletId) {
      setSelectedOutlet(outlets[0].id);
    }
  }, [outlets, selectedOutletId, setSelectedOutlet]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  if (!outlets || outlets.length === 0) return null;

  const selected = outlets.find((o) => o.id === selectedOutletId) ?? outlets[0];

  // Single outlet — just show the name
  if (outlets.length === 1) {
    if (collapsed) {
      return (
        <div className="px-3 py-2" title={selected.outlet_name}>
          <span className="material-symbols-outlined text-xl text-on-surface-variant">
            store
          </span>
        </div>
      );
    }
    return (
      <div className="px-3 py-2 flex items-center gap-2">
        <span className="material-symbols-outlined text-xl text-on-surface-variant flex-shrink-0">
          store
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-on-surface truncate">
            {selected.outlet_name}
          </p>
          <p className="text-[10px] text-on-surface-variant truncate">
            {selected.city}
          </p>
        </div>
      </div>
    );
  }

  // Multiple outlets — dropdown
  if (collapsed) {
    return (
      <div className="relative" ref={ref}>
        <button
          onClick={() => setOpen((v) => !v)}
          className="px-3 py-2 rounded-lg hover:bg-surface-container-low transition-colors"
          title={selected.outlet_name}
        >
          <span className="material-symbols-outlined text-xl text-on-surface-variant">
            store
          </span>
        </button>
        {open && (
          <div className="absolute left-full top-0 ml-2 w-48 bg-surface-container-lowest rounded-xl shadow-ambient z-50 py-1">
            {outlets.map((outlet) => (
              <button
                key={outlet.id}
                onClick={() => {
                  setSelectedOutlet(outlet.id);
                  setOpen(false);
                }}
                className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
                  outlet.id === selected.id
                    ? "bg-primary/10 text-primary"
                    : "text-on-surface hover:bg-surface-container-low"
                }`}
              >
                <p className="font-semibold truncate">{outlet.outlet_name}</p>
                <p className="text-xs text-on-surface-variant">{outlet.city}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-container-low transition-colors"
      >
        <span className="material-symbols-outlined text-xl text-on-surface-variant flex-shrink-0">
          store
        </span>
        <div className="flex-1 min-w-0 text-left">
          <p className="text-xs font-semibold text-on-surface truncate">
            {selected.outlet_name}
          </p>
          <p className="text-[10px] text-on-surface-variant truncate">
            {selected.city}
          </p>
        </div>
        <span className="material-symbols-outlined text-base text-on-surface-variant flex-shrink-0">
          {open ? "expand_less" : "expand_more"}
        </span>
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full mt-1 bg-surface-container-lowest rounded-xl shadow-ambient z-50 py-1">
          {outlets.map((outlet) => (
            <button
              key={outlet.id}
              onClick={() => {
                setSelectedOutlet(outlet.id);
                setOpen(false);
              }}
              className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
                outlet.id === selected.id
                  ? "bg-primary/10 text-primary"
                  : "text-on-surface hover:bg-surface-container-low"
              }`}
            >
              <p className="font-semibold truncate">{outlet.outlet_name}</p>
              <p className="text-xs text-on-surface-variant">{outlet.city}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
