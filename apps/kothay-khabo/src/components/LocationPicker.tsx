import { useState } from "react";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

const AREAS = [
  { name: "Uttara", postcode: "1230" },
  { name: "Banani", postcode: "1213" },
  { name: "Gulshan", postcode: "1212" },
  { name: "Dhanmondi", postcode: "1205" },
  { name: "Mirpur", postcode: "1216" },
  { name: "Bashundhara", postcode: "1229" },
  { name: "Mohammadpur", postcode: "1207" },
  { name: "Motijheel", postcode: "1000" },
];

export default function LocationPicker({
  current, onSelect, onDetect, detecting,
}: {
  current: { area: string; postcode: string } | null;
  onSelect: (area: string, postcode: string) => void;
  onDetect: () => void;
  detecting: boolean;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-lg bg-surface-container-lowest px-3 py-2 text-sm text-on-surface shadow-ambient transition hover:bg-surface-container-low"
      >
        <Icon name="location_on" className="text-primary text-base" />
        {current ? current.area : "Select area"}
        <Icon name="expand_more" className="text-on-surface-variant text-base" />
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 z-50 rounded-lg bg-surface-container-lowest shadow-ambient overflow-hidden w-56">
          <button
            onClick={() => { onDetect(); setOpen(false); }}
            disabled={detecting}
            className="w-full flex items-center gap-2 px-4 py-3 text-sm text-primary font-medium hover:bg-surface-container-low transition"
          >
            <Icon name="my_location" className="text-base" />
            {detecting ? "Detecting..." : "Use my location"}
          </button>
          {AREAS.map((area) => (
            <button
              key={area.name}
              onClick={() => { onSelect(area.name, area.postcode); setOpen(false); }}
              className={`w-full flex items-center gap-2 px-4 py-3 text-sm text-left transition ${
                current?.area === area.name ? "bg-primary/5 text-primary font-medium" : "text-on-surface hover:bg-surface-container-low"
              }`}
            >
              {area.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
