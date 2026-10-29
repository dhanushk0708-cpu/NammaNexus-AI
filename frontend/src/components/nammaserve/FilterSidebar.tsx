'use client';

import React, { useState } from "react";
import {
  MapPin,
  Crosshair,
  Settings,
  Filter,
  Star,
  Check,
  Loader2,
} from "lucide-react";

interface FilterSidebarProps {
  currentLocationName: string;
  postalCode?: string;
  onUseCurrentLocation: () => void;
  onOpenLocationSettings: () => void;
  distanceKm: number;
  onDistanceChange: (val: number) => void;
  priceRange: string;
  onPriceRangeChange: (val: string) => void;
  ratingFilter: number | null;
  onRatingFilterChange: (val: number | null) => void;
  availableToday: boolean;
  onAvailableTodayChange: (val: boolean) => void;
  emergencyOnly: boolean;
  onEmergencyOnlyChange: (val: boolean) => void;
  selectedSources: string[];
  onToggleSource: (source: string) => void;
  isLocating?: boolean;
}

export default function FilterSidebar({
  currentLocationName,
  postalCode = "560060",
  onUseCurrentLocation,
  onOpenLocationSettings,
  distanceKm,
  onDistanceChange,
  priceRange,
  onPriceRangeChange,
  ratingFilter,
  onRatingFilterChange,
  availableToday,
  onAvailableTodayChange,
  emergencyOnly,
  onEmergencyOnlyChange,
  selectedSources,
  onToggleSource,
  isLocating = false,
}: FilterSidebarProps) {
  const sourcesList = [
    { id: "nammaserve", label: "NammaServe Verified" },
    { id: "urban_company", label: "Urban Company" },
    { id: "nobroker", label: "NoBroker" },
    { id: "justdial", label: "Justdial" },
    { id: "sulekha", label: "Sulekha" },
    { id: "other", label: "Other Websites" },
  ];

  return (
    <div className="w-full space-y-4">
      {/* 1. Your Location Card matching screenshot */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-2xs space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-red-50 flex items-center justify-center">
              <MapPin className="w-3.5 h-3.5 text-[#C8102E]" />
            </div>
            <span className="text-xs font-bold text-slate-900">Your Location</span>
          </div>

          <button
            type="button"
            onClick={onOpenLocationSettings}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100 transition-colors cursor-pointer"
            title="Configure Location"
          >
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>

        <p className="text-xs font-semibold text-slate-800 leading-snug pl-1">
          {currentLocationName}, {postalCode}
        </p>

        {/* Geolocation only after explicit user action */}
        <button
          type="button"
          onClick={onUseCurrentLocation}
          disabled={isLocating}
          className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-blue-600 hover:text-blue-800 transition-colors cursor-pointer disabled:opacity-60 pl-1"
        >
          {isLocating ? (
            <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
          ) : (
            <Crosshair className="w-3 h-3 text-blue-600" />
          )}
          <span>{isLocating ? "Detecting GPS..." : "Use Current Location"}</span>
        </button>
      </div>

      {/* 2. Filters Card matching screenshot */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-2xs space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
          <Filter className="w-3.5 h-3.5 text-amber-600" />
          <span className="text-xs font-bold text-slate-900">Filters</span>
        </div>

        {/* Distance Slider */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-700">Distance</span>
            <span className="font-bold text-blue-600">{distanceKm} km</span>
          </div>
          <input
            type="range"
            min="1"
            max="20"
            step="1"
            value={distanceKm}
            onChange={(e) => onDistanceChange(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-[10px] text-slate-400 font-medium">
            <span>0 km</span>
            <span>20 km</span>
          </div>
        </div>

        {/* Price Range Dropdown */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700 block">
            Price Range
          </label>
          <select
            value={priceRange}
            onChange={(e) => onPriceRangeChange(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 text-xs font-medium text-slate-800 rounded-xl px-2.5 py-2 focus:outline-hidden focus:border-amber-400 cursor-pointer"
          >
            <option value="any">Any Price</option>
            <option value="under_500">Under ₹500</option>
            <option value="500_1500">₹500 – ₹1,500</option>
            <option value="above_1500">Above ₹1,500</option>
          </select>
        </div>

        {/* Rating Filter */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-700 block">
            Rating
          </label>
          <div className="flex items-center gap-2 text-xs">
            <div className="flex items-center gap-0.5 text-amber-400">
              <Star className="w-3.5 h-3.5 fill-current" />
              <Star className="w-3.5 h-3.5 fill-current" />
              <Star className="w-3.5 h-3.5 fill-current" />
              <Star className="w-3.5 h-3.5 fill-current" />
              <Star className="w-3.5 h-3.5 text-slate-300" />
            </div>

            <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer ml-auto">
              <input
                type="checkbox"
                checked={ratingFilter === 4}
                onChange={(e) => onRatingFilterChange(e.target.checked ? 4 : null)}
                className="rounded border-slate-300 text-blue-600 focus:ring-0"
              />
              <span>4+ only</span>
            </label>
          </div>
        </div>

        {/* Availability Checkboxes */}
        <div className="space-y-2 pt-2 border-t border-slate-100">
          <label className="text-xs font-semibold text-slate-700 block">
            Availability
          </label>
          <div className="space-y-1.5 text-xs">
            <label className="flex items-center gap-2 text-slate-600 cursor-pointer hover:text-slate-900">
              <input
                type="checkbox"
                checked={availableToday}
                onChange={(e) => onAvailableTodayChange(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-0"
              />
              <span>Available Today</span>
            </label>
            <label className="flex items-center gap-2 text-slate-600 cursor-pointer hover:text-slate-900">
              <input
                type="checkbox"
                checked={emergencyOnly}
                onChange={(e) => onEmergencyOnlyChange(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-0"
              />
              <span>24/7 Service</span>
            </label>
          </div>
        </div>

        {/* Source Checkboxes */}
        <div className="space-y-2 pt-2 border-t border-slate-100">
          <label className="text-xs font-semibold text-slate-700 block">
            Source
          </label>
          <div className="space-y-1.5 text-xs">
            {sourcesList.map((src) => {
              const isChecked = selectedSources.includes(src.id);
              return (
                <label
                  key={src.id}
                  className="flex items-center gap-2 text-slate-600 cursor-pointer hover:text-slate-900"
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => onToggleSource(src.id)}
                    className="rounded border-slate-300 text-blue-600 focus:ring-0"
                  />
                  <span>{src.label}</span>
                </label>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
