'use client';

import React, { useState } from "react";
import { X, Copy, Check, Sparkles, MapPin, Calendar, Tag, ShieldCheck, ExternalLink } from "lucide-react";
import { PromotionItem, PromotionOfferItem, saveClaimedCoupon, claimCoupon } from "@/lib/nammadealsApi";

interface OfferDetailModalProps {
  promotion: PromotionItem | null;
  offer: PromotionOfferItem | null;
  onClose: () => void;
  onClaimed?: () => void;
}

export default function OfferDetailModal({
  promotion,
  offer,
  onClose,
  onClaimed,
}: OfferDetailModalProps) {
  const [copied, setCopied] = useState(false);
  const [claimed, setClaimed] = useState(false);

  if (!promotion || !offer) return null;

  const getFullImageUrl = (url?: string | null) => {
    if (!url) return null;
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    const base = process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") || "http://localhost:8000";
    return `${base}${url}`;
  };

  const imageUrl = getFullImageUrl(promotion.advertisement_image_url);

  const handleCopy = () => {
    if (offer.coupon_code) {
      navigator.clipboard.writeText(offer.coupon_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleClaim = async () => {
    try {
      const citizenId = "citizen_current_user";
      const serverClaim = await claimCoupon(offer.id, citizenId).catch(() => null);
      const uniqueCode = serverClaim?.unique_coupon_code || offer.coupon_code || "REWARD";

      saveClaimedCoupon({
        id: serverClaim?.id || `${offer.id}_${Date.now()}`,
        campaign_id: promotion.campaign_id,
        campaign_name: promotion.campaign_name,
        business_name: promotion.business_name,
        business_area: promotion.business_area,
        offer_title: offer.title,
        coupon_code: uniqueCode,
        discount_label:
          offer.discount_type === "PERCENTAGE"
            ? `${offer.discount_value}% OFF`
            : offer.discount_type === "FLAT"
            ? `₹${offer.discount_value} OFF`
            : "SPECIAL DEAL",
        valid_until: offer.valid_until,
        claimed_at: new Date().toISOString(),
        is_used: false,
      });
      setClaimed(true);
      if (onClaimed) onClaimed();
    } catch {
      // Fallback to local save if offline
      if (offer.coupon_code) {
        saveClaimedCoupon({
          id: `${offer.id}_${Date.now()}`,
          campaign_id: promotion.campaign_id,
          campaign_name: promotion.campaign_name,
          business_name: promotion.business_name,
          business_area: promotion.business_area,
          offer_title: offer.title,
          coupon_code: offer.coupon_code,
          discount_label: `${offer.discount_value}% OFF`,
          valid_until: offer.valid_until,
          claimed_at: new Date().toISOString(),
          is_used: false,
        });
        setClaimed(true);
        if (onClaimed) onClaimed();
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-lg w-full overflow-hidden shadow-2xl border border-slate-200 relative max-h-[90vh] flex flex-col">
        {/* Top Accent Gradient */}
        <div className="h-2 w-full bg-gradient-to-r from-[#C8102E] via-[#FFC72C] to-[#C8102E] shrink-0" />

        {/* Visual Promotional Banner Image */}
        {imageUrl && (
          <div className="w-full h-44 overflow-hidden bg-slate-100 border-b border-slate-100 shrink-0">
            <img src={imageUrl} alt={promotion.campaign_name} className="w-full h-full object-cover" />
          </div>
        )}

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-500 hover:text-slate-800 rounded-full bg-white/80 hover:bg-white shadow-xs transition-colors z-20"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-6 sm:p-8 space-y-5 overflow-y-auto">
          {/* Business & Category Header */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-[#C8102E] uppercase bg-red-50 border border-red-200 px-2.5 py-0.5 rounded-full">
                {promotion.business_category}
              </span>
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                {promotion.business_area}
                {promotion.distance_km != null && ` • ${promotion.distance_km} km away`}
              </span>
            </div>
            <h3 className="text-xl font-black text-slate-900">{promotion.business_name}</h3>

            {promotion.store_maps_url && (
              <div>
                <a
                  href={promotion.store_maps_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-3 py-1.5 rounded-lg transition-colors mt-1"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>View Store Location on Google Maps</span>
                </a>
              </div>
            )}
          </div>

          {/* Offer Highlight Box */}
          <div className="bg-gradient-to-br from-red-50/70 to-amber-50/50 border border-red-200/80 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-800 bg-amber-100/80 px-2.5 py-1 rounded-md flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                Exclusive Civic Reward
              </span>
              <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                Valid till {new Date(offer.valid_until).toLocaleDateString()}
              </span>
            </div>
            <h4 className="text-lg font-bold text-slate-900">{offer.title}</h4>
            {offer.description && (
              <p className="text-xs text-slate-600 leading-relaxed">{offer.description}</p>
            )}

            {/* Coupon Code Box */}
            {offer.coupon_code && (
              <div className="pt-2">
                <div className="flex items-center justify-between bg-white border-2 border-dashed border-red-300 rounded-xl p-3">
                  <div className="space-y-0.5">
                    <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Coupon Code</span>
                    <div className="font-mono text-base font-black text-[#C8102E] tracking-widest">
                      {offer.coupon_code}
                    </div>
                  </div>
                  <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 text-xs font-bold bg-red-50 hover:bg-red-100 text-[#C8102E] px-3.5 py-2 rounded-lg transition-colors"
                  >
                    {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                    <span>{copied ? "Copied" : "Copy"}</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Terms & Conditions */}
          {offer.terms_and_conditions && (
            <div className="space-y-1.5">
              <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide flex items-center gap-1">
                <Tag className="w-3.5 h-3.5 text-slate-400" />
                Terms & Conditions
              </h5>
              <p className="text-xs text-slate-500 bg-slate-50 rounded-xl p-3 border border-slate-200 leading-relaxed">
                {offer.terms_and_conditions}
              </p>
            </div>
          )}

          {/* Redemption Instructions */}
          <div className="space-y-2 text-xs text-slate-600 bg-emerald-50/50 border border-emerald-200/80 rounded-xl p-3.5 flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <p>
              Present this coupon code in-store at <span className="font-semibold text-slate-900">{promotion.business_name}</span> or mention it during billing to redeem your reward.
            </p>
          </div>

          {/* Actions */}
          <div className="pt-2 flex items-center gap-3">
            <button
              onClick={handleClaim}
              disabled={claimed}
              className={`flex-1 py-3 px-4 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
                claimed
                  ? "bg-emerald-600 text-white cursor-default"
                  : "bg-[#C8102E] hover:bg-[#A60C24] text-white shadow-md"
              }`}
            >
              {claimed ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Saved to My Coupons!</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-amber-300" />
                  <span>Claim Offer & Save</span>
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="py-3 px-5 rounded-xl border border-slate-200 font-semibold text-sm text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
