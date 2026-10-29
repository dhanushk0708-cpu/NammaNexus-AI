'use client';

import React from "react";
import {
  Crosshair,
  Star,
  Phone,
  Globe,
  Navigation,
  CheckCircle2,
  ArrowRight,
  AlertCircle,
} from "lucide-react";

export interface ProviderItem {
  id: string;
  number: number;
  name: string;
  isVerified: boolean;
  isPartiallyVerified?: boolean;
  verificationStatus?: string;
  rating: number | null;
  reviewsCount: number | null;
  distanceKm: number | null;
  locality: string;
  matchedServices: string;
  priceDisplay: string;
  phone?: string | null;
  websiteUrl?: string;
  latitude: number;
  longitude: number;
  imageUrl?: string;
  isDemoFixture?: boolean;
  source?: string;
  evidenceNotes?: string;
}

interface NearbyProvidersListProps {
  serviceName: string;
  providers: ProviderItem[];
  selectedProviderId: string | null;
  onSelectProvider: (provider: ProviderItem) => void;
  isLoading?: boolean;
}

export default function NearbyProvidersList({
  serviceName,
  providers,
  selectedProviderId,
  onSelectProvider,
  isLoading = false,
}: NearbyProvidersListProps) {
  return (
    <div className="w-full bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 shadow-2xs space-y-4">
      {/* Header matching screenshot */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-blue-50 flex items-center justify-center shrink-0">
            <Crosshair className="w-3.5 h-3.5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-extrabold text-slate-900 leading-tight">
              Nearby {serviceName} Providers ({providers.length > 0 ? `Top ${providers.length}` : "0"})
            </h3>
            <p className="text-[11px] text-slate-500 font-medium">
              Local businesses near you from our database and open sources
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            const el = document.getElementById("nammaserve-results-anchor");
            if (el) el.scrollIntoView({ behavior: "smooth" });
          }}
          className="text-xs font-bold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 transition-colors self-start sm:self-center cursor-pointer"
        >
          <span>View All</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-2">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-medium">Searching verified Bengaluru providers...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && providers.length === 0 && (
        <div className="py-10 text-center space-y-2 bg-slate-50 rounded-xl p-4 border border-dashed border-slate-200">
          <AlertCircle className="w-8 h-8 text-amber-500 mx-auto" />
          <h4 className="text-xs font-bold text-slate-800">No verified providers found</h4>
          <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
            Try expanding your search radius or selecting a nearby Bengaluru locality.
          </p>
        </div>
      )}

      {/* Provider List matching screenshot cards */}
      {!isLoading && providers.length > 0 && (
        <div className="space-y-3.5" id="nammaserve-results-anchor">
          {providers.map((provider) => {
            const isSelected = selectedProviderId === provider.id;

            return (
              <div
                key={provider.id}
                onClick={() => onSelectProvider(provider)}
                className={`relative bg-white border rounded-2xl p-3.5 sm:p-4 shadow-2xs hover:shadow-md transition-all cursor-pointer flex flex-col sm:flex-row gap-3.5 items-start sm:items-center justify-between ${
                  isSelected
                    ? "border-blue-500 ring-2 ring-blue-100 bg-blue-50/20"
                    : "border-slate-200/90 hover:border-slate-300"
                }`}
              >
                {/* Content Container */}
                <div className="flex items-start gap-3 w-full">
                  {/* Number Badge */}
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center font-black text-xs shrink-0 mt-0.5 shadow-2xs ${
                      provider.number === 1
                        ? "bg-amber-400 text-amber-950"
                        : provider.number === 2
                        ? "bg-slate-300 text-slate-800"
                        : "bg-amber-700/80 text-white"
                    }`}
                  >
                    {provider.number}
                  </div>

                  {/* Never imply a stock image belongs to a returned business. */}
                  <div className="w-16 h-16 sm:w-18 sm:h-18 rounded-xl bg-slate-100 shrink-0 border border-slate-200 flex items-center justify-center text-lg font-black text-slate-400" aria-label="No business image supplied by source">
                    {provider.name.slice(0, 1).toUpperCase()}
                  </div>

                  {/* Details */}
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <div className="flex items-center gap-1.5 truncate">
                        <h4 className="text-xs sm:text-sm font-extrabold text-slate-900 truncate">
                          {provider.name}
                        </h4>
                        {provider.isVerified && (
                          <span className="inline-flex items-center gap-0.5 text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-1 py-0.2 rounded shrink-0">
                            <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" />
                            <span>Verified</span>
                          </span>
                        )}
                        {provider.isPartiallyVerified && (
                          <span className="inline-flex items-center gap-0.5 text-[9px] font-bold bg-amber-50 text-amber-700 border border-amber-200 px-1 py-0.2 rounded shrink-0">
                            <span>Partially Verified</span>
                          </span>
                        )}
                      </div>
                      {provider.isDemoFixture && (
                        <span className="text-[8px] font-bold bg-amber-50 text-amber-700 border border-amber-200 px-1 py-0.2 rounded shrink-0 uppercase tracking-wider">
                          Demo Data
                        </span>
                      )}
                    </div>

                    {/* Rating & Reviews */}
                    {provider.rating !== null && provider.reviewsCount !== null ? (
                      <div className="flex items-center gap-1 text-[11px] text-slate-600">
                        <div className="flex items-center text-amber-500">
                          <Star className="w-3 h-3 fill-current" />
                        </div>
                        <span className="font-bold text-slate-900">{provider.rating.toFixed(1)}</span>
                        <span className="text-slate-400">({provider.reviewsCount} reviews)</span>
                      </div>
                    ) : (
                      <p className="text-[10px] text-slate-400 italic">No verified review data available.</p>
                    )}

                    {/* Distance & Locality */}
                    <p className="text-[11px] text-slate-500 font-medium truncate">
                      {provider.distanceKm !== null ? `${provider.distanceKm.toFixed(1)} km • ` : ""}
                      {provider.locality}
                    </p>

                    {/* Services */}
                    <p className="text-[11px] text-slate-600 truncate">
                      {provider.matchedServices}
                    </p>

                    {/* Evidence Notes if present */}
                    {provider.evidenceNotes && (
                      <p className="text-[10px] text-slate-500 italic truncate" title={provider.evidenceNotes}>
                        Note: {provider.evidenceNotes}
                      </p>
                    )}

                    {/* Price & Action Buttons Row matching screenshot */}
                    <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100">
                      <p className="text-xs font-black text-slate-900">
                        {provider.priceDisplay}
                      </p>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {provider.phone && provider.phone.trim() && !provider.phone.toLowerCase().includes("contact") && !provider.phone.toLowerCase().includes("see source") && (
                          <a
                            href={`tel:${provider.phone}`}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-2 py-1 rounded-md text-[11px] font-semibold shadow-2xs transition-colors"
                            title={`Call ${provider.phone}`}
                          >
                            <Phone className="w-3 h-3 text-emerald-600" />
                            <span>Call</span>
                          </a>
                        )}

                        {provider.websiteUrl && (
                          <a
                            href={provider.websiteUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-2 py-1 rounded-md text-[11px] font-semibold shadow-2xs transition-colors"
                            title="Open Official Website or Evidence Source"
                          >
                            <Globe className="w-3 h-3 text-blue-600" />
                            <span>Source</span>
                          </a>
                        )}

                        <a
                          href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                            `${provider.name} ${provider.locality} Bengaluru`
                          )}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-2 py-1 rounded-md text-[11px] font-semibold shadow-2xs transition-colors"
                          title="Get Directions"
                        >
                          <Navigation className="w-3 h-3 text-amber-600" />
                          <span>Directions</span>
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
