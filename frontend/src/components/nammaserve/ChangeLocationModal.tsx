'use client';

import React, { useState } from "react";
import { X, MapPin, Check, Crosshair, Search } from "lucide-react";

interface ChangeLocationModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentLocality: string;
  onSelectLocality: (locality: string, lat: number, lng: number) => void;
}

const BENGALURU_AREAS = [
  { name: "Kengeri", lat: 12.9177, lng: 77.4838, pincode: "560060" },
  { name: "Indiranagar", lat: 12.9784, lng: 77.6408, pincode: "560038" },
  { name: "Koramangala", lat: 12.9352, lng: 77.6245, pincode: "560034" },
  { name: "Whitefield", lat: 12.9698, lng: 77.7500, pincode: "560066" },
  { name: "HSR Layout", lat: 12.9121, lng: 77.6446, pincode: "560102" },
  { name: "Jayanagar", lat: 12.9308, lng: 77.5838, pincode: "560041" },
  { name: "Malleswaram", lat: 13.0031, lng: 77.5643, pincode: "560003" },
  { name: "BTM Layout", lat: 12.9166, lng: 77.6101, pincode: "560068" },
  { name: "Yelahanka", lat: 13.1007, lng: 77.5963, pincode: "560064" },
  { name: "Electronic City", lat: 12.8452, lng: 77.6602, pincode: "560100" },
  { name: "Hebbal", lat: 13.0358, lng: 77.5970, pincode: "560024" },
  { name: "Rajajinagar", lat: 12.9915, lng: 77.5530, pincode: "560010" },
];

export default function ChangeLocationModal({
  isOpen,
  onClose,
  currentLocality,
  onSelectLocality,
}: ChangeLocationModalProps) {
  const [query, setQuery] = useState("");

  if (!isOpen) return null;

  const filtered = BENGALURU_AREAS.filter((a) =>
    a.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="w-full max-w-md bg-white rounded-3xl border border-slate-200 shadow-2xl p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-amber-50 flex items-center justify-center">
              <MapPin className="w-4 h-4 text-amber-600" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">Change Bengaluru Locality</h3>
              <p className="text-[11px] text-slate-500">Select your active neighborhood</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search input */}
        <div className="relative flex items-center bg-slate-50 rounded-xl border border-slate-200 px-3 py-2">
          <Search className="w-4 h-4 text-slate-400 mr-2 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type area name (e.g. Indiranagar, HSR)..."
            className="w-full bg-transparent text-xs sm:text-sm font-medium text-slate-800 placeholder:text-slate-400 focus:outline-hidden"
            autoFocus
          />
        </div>

        {/* Neighborhood chips */}
        <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
          {filtered.map((area) => {
            const isCurrent = currentLocality.toLowerCase().includes(area.name.toLowerCase());
            return (
              <button
                key={area.name}
                type="button"
                onClick={() => {
                  onSelectLocality(area.name, area.lat, area.lng);
                  onClose();
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                  isCurrent
                    ? "bg-amber-50 text-slate-900 border border-amber-300 font-bold"
                    : "hover:bg-slate-50 text-slate-700"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <MapPin className={`w-3.5 h-3.5 ${isCurrent ? "text-amber-600" : "text-slate-400"}`} />
                  <span>{area.name}, Bengaluru</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400">{area.pincode}</span>
                  {isCurrent && <Check className="w-3.5 h-3.5 text-amber-600" />}
                </div>
              </button>
            );
          })}

          {filtered.length === 0 && (
            <div className="py-6 text-center text-xs text-slate-400">
              No matching locality. You can search directly using the top search bar.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
