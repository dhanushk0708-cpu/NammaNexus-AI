'use client';

import React from "react";
import { Search, MapPin, Crosshair, ChevronDown, X, Loader2 } from "lucide-react";

interface TopSearchBarProps {
  serviceQuery: string;
  onServiceQueryChange: (val: string) => void;
  localityQuery: string;
  onLocalityQueryChange: (val: string) => void;
  radiusKm: number;
  onRadiusKmChange: (val: number) => void;
  onSearchSubmit: () => void;
  isLoading?: boolean;
}

export default function TopSearchBar({
  serviceQuery,
  onServiceQueryChange,
  localityQuery,
  onLocalityQueryChange,
  radiusKm,
  onRadiusKmChange,
  onSearchSubmit,
  isLoading = false,
}: TopSearchBarProps) {
  const radiusOptions = [
    { label: "Within 2 km", value: 2 },
    { label: "Within 5 km", value: 5 },
    { label: "Within 10 km", value: 10 },
    { label: "Within 20 km", value: 20 },
  ];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      onSearchSubmit();
    }
  };

  return (
    <div className="w-full bg-white rounded-2xl p-2 sm:p-2.5 border border-slate-200/90 shadow-2xs">
      <div className="grid grid-cols-1 md:grid-cols-12 gap-2 items-center">
        {/* 1. Service Search Input */}
        <div className="md:col-span-5 relative flex items-center bg-slate-50/80 hover:bg-slate-50 focus-within:bg-white rounded-xl border border-slate-200 focus-within:border-amber-400 focus-within:ring-2 focus-within:ring-amber-100 transition-all px-3 py-2">
          <Search className="w-4 h-4 text-slate-400 shrink-0 mr-2" />
          <input
            type="text"
            value={serviceQuery}
            onChange={(e) => onServiceQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search service (e.g. AC repair, water tanker, cleaning)..."
            className="w-full bg-transparent text-xs sm:text-sm font-medium text-slate-900 placeholder:text-slate-400 focus:outline-hidden"
          />
          {serviceQuery && (
            <button
              type="button"
              onClick={() => onServiceQueryChange("")}
              className="text-slate-400 hover:text-slate-600 p-0.5 rounded-full hover:bg-slate-200/60 transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* 2. Manual Locality Input */}
        <div className="md:col-span-4 relative flex items-center bg-slate-50/80 hover:bg-slate-50 focus-within:bg-white rounded-xl border border-slate-200 focus-within:border-amber-400 focus-within:ring-2 focus-within:ring-amber-100 transition-all px-3 py-2">
          <MapPin className="w-4 h-4 text-amber-500 shrink-0 mr-2" />
          <input
            type="text"
            value={localityQuery}
            onChange={(e) => onLocalityQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Locality (e.g. Kengeri, Bengaluru)..."
            className="w-full bg-transparent text-xs sm:text-sm font-medium text-slate-900 placeholder:text-slate-400 focus:outline-hidden"
          />
          {localityQuery && (
            <button
              type="button"
              onClick={() => onLocalityQueryChange("")}
              className="text-slate-400 hover:text-slate-600 p-0.5 rounded-full hover:bg-slate-200/60 transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* 3. Search Radius Dropdown */}
        <div className="md:col-span-2 relative flex items-center bg-slate-50/80 hover:bg-slate-50 focus-within:bg-white rounded-xl border border-slate-200 focus-within:border-amber-400 focus-within:ring-2 focus-within:ring-amber-100 transition-all px-3 py-2">
          <Crosshair className="w-3.5 h-3.5 text-slate-500 shrink-0 mr-2" />
          <select
            value={radiusKm}
            onChange={(e) => onRadiusKmChange(Number(e.target.value))}
            className="w-full bg-transparent text-xs sm:text-sm font-semibold text-slate-800 focus:outline-hidden appearance-none cursor-pointer pr-4"
          >
            {radiusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-3 pointer-events-none" />
        </div>

        {/* 4. Search Button */}
        <div className="md:col-span-1 flex items-center justify-stretch">
          <button
            type="button"
            onClick={onSearchSubmit}
            disabled={isLoading}
            className="w-full bg-[#C8102E] hover:bg-[#A60C24] active:scale-[0.98] text-white font-bold text-xs sm:text-sm py-2.5 px-4 rounded-xl shadow-xs transition-all flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-75"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>Search</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
