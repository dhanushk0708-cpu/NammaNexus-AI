'use client';

import React from "react";
import { MapPin, Edit3, Map as MapIcon } from "lucide-react";

interface LocationBannerProps {
  serviceName: string;
  locality: string;
  radiusKm: number;
  onChangeLocationClick: () => void;
  onMapViewClick: () => void;
  isMapViewActive?: boolean;
}

export default function LocationBanner({
  serviceName,
  locality,
  radiusKm,
  onChangeLocationClick,
  onMapViewClick,
  isMapViewActive = false,
}: LocationBannerProps) {
  return (
    <div className="w-full bg-[#FFFBEB] border border-amber-200/90 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-2xs">
      {/* Left Icon & Text */}
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-full bg-amber-100 border border-amber-300/80 flex items-center justify-center shrink-0 shadow-2xs">
          <MapPin className="w-5 h-5 text-amber-700" />
        </div>
        <div>
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Showing results for
          </span>
          <h1 className="text-base sm:text-lg font-extrabold text-slate-900 leading-tight">
            {serviceName} near {locality}
          </h1>
          <p className="text-[11px] text-slate-600 font-medium mt-0.5 flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Based on selected location</span>
            <span>•</span>
            <span>{radiusKm} km radius</span>
          </p>
        </div>
      </div>

      {/* Right Action Buttons matching screenshot */}
      <div className="flex items-center gap-2.5 shrink-0 self-end sm:self-center">
        <button
          type="button"
          onClick={onChangeLocationClick}
          className="inline-flex items-center gap-1.5 bg-white hover:bg-amber-50/60 text-slate-700 border border-amber-300 font-bold text-xs px-3.5 py-2 rounded-xl shadow-2xs transition-colors cursor-pointer"
        >
          <Edit3 className="w-3.5 h-3.5 text-amber-600" />
          <span>Change Location</span>
        </button>

        <button
          type="button"
          onClick={onMapViewClick}
          className={`inline-flex items-center gap-1.5 border font-bold text-xs px-3.5 py-2 rounded-xl shadow-2xs transition-all cursor-pointer ${
            isMapViewActive
              ? "bg-amber-500 text-white border-amber-600 ring-2 ring-amber-200"
              : "bg-white hover:bg-amber-50/60 text-slate-700 border-amber-300"
          }`}
        >
          <MapIcon className={`w-3.5 h-3.5 ${isMapViewActive ? "text-white" : "text-amber-600"}`} />
          <span>Map View</span>
        </button>
      </div>
    </div>
  );
}
