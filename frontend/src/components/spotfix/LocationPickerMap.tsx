'use client';

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { MapPin, Navigation, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";

const DynamicMap = dynamic(() => import("./DynamicMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-72 bg-slate-100 border border-slate-200 rounded-xl flex items-center justify-center text-slate-500 text-xs gap-2">
      <RefreshCw className="w-5 h-5 animate-spin text-[#C8102E]" />
      Initializing SpotFix Leaflet Map...
    </div>
  ),
});

interface LocationPickerMapProps {
  onLocationConfirmed: (lat: number, lng: number) => void;
  initialLat?: number | null;
  initialLng?: number | null;
}

const DEFAULT_LAT = 12.9716;
const DEFAULT_LNG = 77.5946;

export default function LocationPickerMap({
  onLocationConfirmed,
  initialLat,
  initialLng,
}: LocationPickerMapProps) {
  const [lat, setLat] = useState<number>(initialLat ?? DEFAULT_LAT);
  const [lng, setLng] = useState<number>(initialLng ?? DEFAULT_LNG);
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  const fetchBrowserLocation = () => {
    if (!navigator.geolocation) {
      setLocationError("Geolocation is not supported by your browser.");
      return;
    }

    setIsLocating(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLng(pos.coords.longitude);
        setIsLocating(false);
      },
      (err) => {
        console.error("Geolocation error:", err);
        setIsLocating(false);
        let msg = "Could not retrieve your location.";
        if (err.code === err.PERMISSION_DENIED) {
          msg = "Location permission was denied. Please click on the map to set your location.";
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          msg = "Location information is unavailable. Please click on the map to set location.";
        } else if (err.code === err.TIMEOUT) {
          msg = "Location request timed out. Please click on the map manually.";
        }
        setLocationError(msg);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  useEffect(() => {
    if (initialLat === null || initialLat === undefined) {
      fetchBrowserLocation();
    }
  }, []);

  const handlePositionChange = (newLat: number, newLng: number) => {
    setLat(newLat);
    setLng(newLng);
    setLocationError(null);
  };

  const handleConfirm = () => {
    onLocationConfirmed(lat, lng);
  };

  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl p-6 shadow-xs text-slate-900 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-[#C8102E]" />
            Step 2: Confirm Location on Map
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Click anywhere on the map or drag the marker to pin the exact complaint location.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchBrowserLocation}
          disabled={isLocating}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl border border-slate-300 transition-all disabled:opacity-50 shrink-0"
        >
          {isLocating ? (
            <RefreshCw className="w-4 h-4 animate-spin text-[#C8102E]" />
          ) : (
            <Navigation className="w-4 h-4 text-[#C8102E]" />
          )}
          Detect Current Location
        </button>
      </div>

      {locationError && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <p>{locationError}</p>
        </div>
      )}

      <div className="relative w-full h-80 rounded-xl overflow-hidden border border-slate-200 bg-slate-50">
        <DynamicMap lat={lat} lng={lng} onPositionChange={handlePositionChange} />
      </div>

      <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <span className="text-[11px] uppercase tracking-wider text-slate-500 font-bold block">
            Selected Coordinates
          </span>
          <p className="text-xs font-mono text-[#C8102E] font-bold">
            Latitude: <span className="text-slate-900">{lat.toFixed(6)}</span> | Longitude:{" "}
            <span className="text-slate-900">{lng.toFixed(6)}</span>
          </p>
        </div>

        <button
          type="button"
          onClick={handleConfirm}
          className="w-full sm:w-auto px-6 py-3 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 shrink-0"
        >
          <CheckCircle2 className="w-4 h-4 text-amber-300" />
          Confirm Map Location
        </button>
      </div>
    </div>
  );
}
