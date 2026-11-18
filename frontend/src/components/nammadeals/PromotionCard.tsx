'use client';

import React, { useEffect, useRef } from "react";
import { Tag, MapPin, Sparkles, ArrowRight, ShieldCheck, Clock } from "lucide-react";
import { PromotionItem, PromotionOfferItem, recordPromotionEvent } from "@/lib/nammadealsApi";

interface PromotionCardProps {
  promotion: PromotionItem;
  citizenUserId?: string;
  onSelectOffer: (promotion: PromotionItem, offer: PromotionOfferItem) => void;
}

export default function PromotionCard({
  promotion,
  citizenUserId,
  onSelectOffer,
}: PromotionCardProps) {
  const hasRecordedImpression = useRef(false);

  useEffect(() => {
    if (!hasRecordedImpression.current && promotion.campaign_id) {
      hasRecordedImpression.current = true;
      recordPromotionEvent(
        {
          event_type: "IMPRESSION",
          campaign_id: promotion.campaign_id,
          location_source: promotion.matched_location_source,
          idempotency_key: `imp_${promotion.campaign_id}_${Date.now()}`,
        },
        citizenUserId
      );
    }
  }, [promotion.campaign_id, promotion.matched_location_source, citizenUserId]);

  const primaryOffer = promotion.offers && promotion.offers.length > 0 ? promotion.offers[0] : null;
  if (!primaryOffer) return null;

  const handleClick = () => {
    recordPromotionEvent(
      {
        event_type: "CLICK",
        campaign_id: promotion.campaign_id,
        offer_id: primaryOffer.id,
        location_source: promotion.matched_location_source,
        idempotency_key: `clk_${promotion.campaign_id}_${Date.now()}`,
      },
      citizenUserId
    );
    onSelectOffer(promotion, primaryOffer);
  };

  const getDiscountBadge = () => {
    if (primaryOffer.discount_type === "PERCENTAGE") {
      return `${primaryOffer.discount_value}% OFF`;
    }
    if (primaryOffer.discount_type === "FLAT") {
      return `₹${primaryOffer.discount_value} OFF`;
    }
    if (primaryOffer.discount_type === "FREEBIE") {
      return "FREE ITEM / BOGO";
    }
    return "CIVIC REWARD";
  };

  const getLocationBadge = () => {
    if (promotion.distance_km != null) {
      return `${promotion.distance_km} km • ${promotion.business_area}`;
    }
    if (promotion.matched_location_source === "ONLINE") {
      return "Online Offer";
    }
    return `${promotion.business_area}`;
  };

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-md hover:border-red-300 transition-all p-5 flex flex-col justify-between cursor-pointer group relative overflow-hidden"
    >
      {/* Top Banner Accent */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#C8102E] to-[#FFC72C] opacity-80 group-hover:opacity-100 transition-opacity" />

      <div className="space-y-3.5">
        {/* Top Badges */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <span className="text-[10px] font-bold tracking-wider uppercase bg-red-50 text-[#C8102E] border border-red-200 px-2 py-0.5 rounded-md">
            {promotion.business_category}
          </span>
          <span className="text-xs font-black text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full flex items-center gap-1 shadow-2xs">
            <Sparkles className="w-3 h-3 text-amber-600" />
            {getDiscountBadge()}
          </span>
        </div>

        {/* Business and Title */}
        <div>
          <h4 className="text-xs text-slate-500 font-semibold tracking-tight">{promotion.business_name}</h4>
          <h3 className="text-base font-extrabold text-slate-900 group-hover:text-[#C8102E] transition-colors line-clamp-1 mt-0.5">
            {primaryOffer.title}
          </h3>
          {primaryOffer.description && (
            <p className="text-xs text-slate-600 line-clamp-2 mt-1 leading-relaxed">
              {primaryOffer.description}
            </p>
          )}
        </div>

        {/* Location & Validity Meta */}
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500 font-medium">
          <span className="flex items-center gap-1 bg-slate-50 px-2 py-0.5 rounded border border-slate-200/60">
            <MapPin className="w-3 h-3 text-slate-400" />
            {getLocationBadge()}
          </span>
          <span className="flex items-center gap-1 text-slate-500">
            <Clock className="w-3 h-3 text-slate-400" />
            Till {new Date(primaryOffer.valid_until).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Action Footer */}
      <div className="mt-4 pt-3 flex items-center justify-between border-t border-slate-100">
        <span className="text-xs font-mono font-bold text-[#C8102E] bg-red-50/70 border border-red-200/60 px-2 py-1 rounded">
          {primaryOffer.coupon_code || "GET DEAL"}
        </span>
        <button
          type="button"
          className="text-xs font-bold text-[#C8102E] flex items-center gap-1 group-hover:translate-x-1 transition-transform"
        >
          <span>Claim Offer</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
