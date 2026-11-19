'use client';

import React, { useState, useEffect } from "react";
import { Sparkles, Gift, ExternalLink, ArrowRight } from "lucide-react";
import Link from "next/link";
import {
  PromotionItem,
  PromotionOfferItem,
  selectPromotions,
} from "@/lib/nammadealsApi";
import PromotionCard from "./PromotionCard";
import OfferDetailModal from "./OfferDetailModal";

interface SpotFixPromotionsProps {
  latitude?: number | null;
  longitude?: number | null;
  area?: string | null;
  citizenUserId?: string;
}

export default function SpotFixPromotions({
  latitude,
  longitude,
  area,
  citizenUserId,
}: SpotFixPromotionsProps) {
  const [promotions, setPromotions] = useState<PromotionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPromo, setSelectedPromo] = useState<PromotionItem | null>(null);
  const [selectedOffer, setSelectedOffer] = useState<PromotionOfferItem | null>(null);

  const loadDeals = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await selectPromotions(
        {
          location_policy: "PREFER_COMPLAINT",
          complaint_location: {
            latitude: latitude || undefined,
            longitude: longitude || undefined,
            area: area || undefined,
          },
          limit: 3,
        },
        citizenUserId
      );
      if (res && res.promotions) {
        setPromotions(res.promotions);
      }
    } catch (e: any) {
      // Must fail safely so complaint submission confirmation is never affected
      console.warn("NammaDeals promotion intake failed safely", e);
      setError("Unable to load promotions at this time.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDeals();
  }, [latitude, longitude, area, citizenUserId]);

  if (loading) {
    return (
      <div className="bg-white/80 rounded-2xl border border-amber-200/80 p-5 space-y-3 animate-pulse">
        <div className="h-4 bg-amber-100/70 rounded w-1/3" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="h-28 bg-slate-100 rounded-xl" />
          <div className="h-28 bg-slate-100 rounded-xl" />
        </div>
      </div>
    );
  }

  // Guaranteed Post-Complaint Display: Never return null
  return (
    <div className="bg-gradient-to-br from-amber-50/60 via-white to-red-50/40 rounded-2xl border border-amber-200 shadow-xs p-6 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-amber-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-amber-500 text-white flex items-center justify-center shrink-0 shadow-2xs">
            <Gift className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-black text-slate-900 flex items-center gap-1.5">
              <span>Civic Rewards for Your Action!</span>
              <span className="text-[10px] font-bold text-amber-800 bg-amber-100/90 px-2 py-0.2 rounded-full">
                Verified Local Deals
              </span>
            </h4>
            <p className="text-xs text-slate-500">
              Local businesses in this neighborhood thank you for helping keep Bengaluru clean and safe.
            </p>
          </div>
        </div>

        <Link
          href="/nammadeals"
          className="text-xs font-bold text-[#C8102E] hover:underline flex items-center gap-1 shrink-0"
        >
          <span>All Rewards</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Promotions Cards Grid or Empty State or Error */}
      {error ? (
        <div className="bg-white/70 border border-slate-200 rounded-xl p-5 text-center space-y-2">
          <p className="text-xs text-slate-600">{error}</p>
          <button
            onClick={loadDeals}
            className="text-xs font-bold text-[#C8102E] hover:underline"
          >
            Retry Loading Offers
          </button>
        </div>
      ) : promotions.length === 0 ? (
        <div className="bg-white/70 border border-amber-200/80 rounded-xl p-6 text-center space-y-2">
          <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center mx-auto">
            <Sparkles className="w-5 h-5" />
          </div>
          <h5 className="text-sm font-bold text-slate-900">New local offers are coming soon!</h5>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Local businesses in your area will be offering exclusive discounts and rewards to civic-minded citizens. Check back soon or browse active city-wide deals.
          </p>
          <div className="pt-2">
            <Link
              href="/nammadeals"
              className="inline-flex items-center gap-1 px-4 py-2 bg-[#C8102E] hover:bg-[#A60C24] text-white rounded-xl text-xs font-bold transition-colors"
            >
              <span>Explore NammaDeals</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {promotions.map((promo) => (
            <PromotionCard
              key={promo.campaign_id}
              promotion={promo}
              citizenUserId={citizenUserId}
              onSelectOffer={(p, o) => {
                setSelectedPromo(p);
                setSelectedOffer(o);
              }}
            />
          ))}
        </div>
      )}

      {/* Offer Detail Modal */}
      {selectedPromo && selectedOffer && (
        <OfferDetailModal
          promotion={selectedPromo}
          offer={selectedOffer}
          onClose={() => {
            setSelectedPromo(null);
            setSelectedOffer(null);
          }}
        />
      )}
    </div>
  );
}
