import { useState } from "react";

const STORAGE_KEY = "kk_location";

type Location = { postcode: string; area: string; lat?: number; lng?: number };

export function useLocation() {
  const [location, setLocation] = useState<Location | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });
  const [detecting, setDetecting] = useState(false);

  function saveLocation(loc: Location) {
    setLocation(loc);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(loc));
  }

  function detectLocation() {
    if (!navigator.geolocation) return;
    setDetecting(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        saveLocation({ postcode: "1230", area: "Uttara", lat: pos.coords.latitude, lng: pos.coords.longitude });
        setDetecting(false);
      },
      () => setDetecting(false),
      { timeout: 5000 }
    );
  }

  return { location, saveLocation, detectLocation, detecting };
}
