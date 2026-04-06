import SearchInput from "../components/SearchInput";
import LocationPicker from "../components/LocationPicker";
import { useLocation } from "../hooks/useLocation";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

export default function SearchPage({ onSearch }: { onSearch: (query: string, postcode?: string) => void }) {
  const { location, saveLocation, detectLocation, detecting } = useLocation();

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <div className="bg-gradient-to-br from-primary to-primary-container px-6 pt-14 pb-24">
        <div className="mx-auto max-w-lg">
          <h1 className="font-headline text-2xl font-extrabold text-white">কোথায় খাবো?</h1>
          <p className="mt-1 text-sm text-white/70">Find the best restaurants in Dhaka</p>
          <div className="mt-6">
            <SearchInput onSearch={(q) => onSearch(q, location?.postcode)} />
          </div>
        </div>
      </div>
      <div className="mx-auto max-w-lg w-full px-6 -mt-6">
        <div className="flex items-center gap-2">
          <LocationPicker
            current={location}
            onSelect={(area, postcode) => saveLocation({ area, postcode })}
            onDetect={detectLocation}
            detecting={detecting}
          />
          {location && <span className="text-xs text-on-surface-variant">Showing restaurants in {location.area}</span>}
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="text-center">
          <Icon name="restaurant" className="text-6xl text-on-surface-variant/20" />
          <p className="mt-3 text-sm text-on-surface-variant">Ask anything — "best biryani nearby" or "quiet café for two"</p>
        </div>
      </div>
    </div>
  );
}
