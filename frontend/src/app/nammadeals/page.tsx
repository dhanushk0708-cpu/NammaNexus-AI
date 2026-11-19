'use client';

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Sparkles,
  Gift,
  MapPin,
  Tag,
  Building2,
  Ticket,
  Clock,
  Copy,
  Check,
  RotateCcw,
  ShieldCheck,
  ChevronRight,
  SlidersHorizontal,
} from "lucide-react";
import {
  PromotionItem,
  PromotionOfferItem,
  ClaimedCoupon,
  getClaimedCoupons,
  selectPromotions,
} from "@/lib/nammadealsApi";
import PromotionCard from "@/components/nammadeals/PromotionCard";
import OfferDetailModal from "@/components/nammadeals/OfferDetailModal";
import ScratchCard from "@/components/nammadeals/ScratchCard";

const BANGALORE_AREAS = [
  { name: "Koramangala", lat: 12.9340, lng: 77.6220, pin: "560034" },
  { name: "Indiranagar", lat: 12.9716, lng: 77.6412, pin: "560038" },
  { name: "Jayanagar", lat: 12.9250, lng: 77.5938, pin: "560041" },
  { name: "Malleshwaram", lat: 12.9982, lng: 77.5703, pin: "560003" },
  { name: "Whitefield", lat: 12.9698, lng: 77.7500, pin: "560066" },
  { name: "HSR Layout", lat: 12.9121, lng: 77.6446, pin: "560102" },
];

export default function NammaDealsPage() {
  const [activeTab, setActiveTab] = useState<"discover" | "my-coupons" | "scratch-cards">("discover");
  const [selectedArea, setSelectedArea] = useState(BANGALORE_AREAS[0]);
  const [promotions, setPromotions] = useState<PromotionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedPromo, setSelectedPromo] = useState<PromotionItem | null>(null);
  const [selectedOffer, setSelectedOffer] = useState<PromotionOfferItem | null>(null);
  const [claimedCoupons, setClaimedCoupons] = useState<ClaimedCoupon[]>([]);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  useEffect(() => {
    setClaimedCoupons(getClaimedCoupons());
  }, []);

  const loadPromotions = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await selectPromotions({
        location_policy: "COMBINED",
        profile_location: {
          city: "Bengaluru",
          area: selectedArea.name,
          pincode: selectedArea.pin,
          latitude: selectedArea.lat,
          longitude: selectedArea.lng,
        },
        limit: 6,
      });
      setPromotions(res.promotions || []);
    } catch (e: any) {
      setError(e.message || "Failed to load promotions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPromotions();
  }, [selectedArea]);

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const scratchCardPromos = promotions.filter((p) =>
    p.offers.some((o) => o.offer_type === "SCRATCH_CARD" || p.campaign_type === "SCRATCH_CARD")
  );

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8 flex-1">
      {/* Hero Banner */}
      <section className="bg-gradient-to-br from-red-50/70 via-white to-amber-50/60 border border-red-200/90 rounded-3xl p-6 sm:p-10 shadow-xs relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#C8102E] via-[#FFC72C] to-[#C8102E]" />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 bg-amber-50 border border-amber-200/80 px-3 py-1 rounded-full text-xs font-bold text-amber-800 uppercase tracking-wider">
              <Gift className="w-3.5 h-3.5 text-amber-600" />
              NammaDeals Civic Rewards & Local Promotions
            </div>

            <h1 className="text-2xl sm:text-4xl font-black text-slate-900 tracking-tight leading-tight">
              Local Bengaluru Deals for <span className="text-[#C8102E]">Active Citizens</span>.
            </h1>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
              Verified local restaurants, bakeries, cafes, and shops offer exclusive promotions, discounts, and mystery scratch-cards to reward civic participation across Bengaluru.
            </p>
          </div>

          {/* Quick Portal Switcher Actions */}
          <div className="flex flex-col sm:flex-row md:flex-col gap-2 shrink-0 w-full sm:w-auto">
            <Link
              href="/nammadeals/business"
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-slate-50 text-slate-800 font-bold px-4 py-2.5 rounded-xl border border-slate-300 text-xs shadow-2xs transition-colors"
            >
              <Building2 className="w-4 h-4 text-[#C8102E]" />
              <span>Business Portal</span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </Link>
            <Link
              href="/nammadeals/admin"
              className="inline-flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 text-white font-bold px-4 py-2.5 rounded-xl text-xs shadow-2xs transition-colors"
            >
              <ShieldCheck className="w-4 h-4 text-amber-300" />
              <span>Admin Management</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Main Tabs Navigation */}
      <div className="flex border-b border-slate-200 gap-6 text-sm font-bold">
        <button
          onClick={() => setActiveTab("discover")}
          className={`pb-3.5 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "discover"
              ? "border-[#C8102E] text-[#C8102E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Discover Local Deals</span>
        </button>

        <button
          onClick={() => setActiveTab("my-coupons")}
          className={`pb-3.5 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "my-coupons"
              ? "border-[#C8102E] text-[#C8102E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Ticket className="w-4 h-4" />
          <span>My Claimed Coupons</span>
          {claimedCoupons.length > 0 && (
            <span className="text-[10px] bg-red-100 text-[#C8102E] px-2 py-0.2 rounded-full font-extrabold">
              {claimedCoupons.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("scratch-cards")}
          className={`pb-3.5 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "scratch-cards"
              ? "border-[#C8102E] text-[#C8102E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Gift className="w-4 h-4 text-amber-500" />
          <span>Mystery Scratch Cards</span>
        </button>
      </div>

      {/* TAB 1: DISCOVER LOCAL DEALS */}
      {activeTab === "discover" && (
        <section className="space-y-6">
          {/* Location Bar */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-2xs">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
              <MapPin className="w-4 h-4 text-[#C8102E]" />
              <span>Target Neighborhood:</span>
              <div className="flex flex-wrap gap-1.5">
                {BANGALORE_AREAS.map((area) => (
                  <button
                    key={area.name}
                    onClick={() => setSelectedArea(area)}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                      selectedArea.name === area.name
                        ? "bg-[#C8102E] text-white shadow-2xs"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {area.name}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={loadPromotions}
              className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1.5 self-end sm:self-auto"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>

          {/* Deals Grid */}
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-48 bg-slate-100 rounded-2xl animate-pulse" />
              ))}
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center text-xs text-red-800">
              <p className="font-bold">Failed to load deals</p>
              <p className="text-slate-500 mt-1">{error}</p>
            </div>
          ) : promotions.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-3xl p-12 text-center space-y-3">
              <Gift className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="text-base font-bold text-slate-800">No active promotions in this area</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Businesses in {selectedArea.name} have not launched active promotions today. Try selecting another area or check back soon!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
              {promotions.map((promo) => (
                <PromotionCard
                  key={promo.campaign_id}
                  promotion={promo}
                  onSelectOffer={(p, o) => {
                    setSelectedPromo(p);
                    setSelectedOffer(o);
                  }}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {/* TAB 2: MY CLAIMED COUPONS */}
      {activeTab === "my-coupons" && (
        <section className="space-y-6">
          {claimedCoupons.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-3xl p-12 text-center space-y-3">
              <Ticket className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="text-base font-bold text-slate-800">No coupons claimed yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Explore local deals and click &quot;Claim Offer&quot; to save coupon codes to your personal rewards drawer.
              </p>
              <button
                onClick={() => setActiveTab("discover")}
                className="inline-flex items-center gap-1.5 text-xs font-bold bg-[#C8102E] text-white px-4 py-2 rounded-xl mt-2"
              >
                Explore Deals Now
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
              {claimedCoupons.map((coupon) => (
                <div
                  key={coupon.id}
                  className="bg-white border-2 border-dashed border-red-200 rounded-2xl p-5 space-y-4 shadow-xs relative overflow-hidden"
                >
                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full inline-block">
                      {coupon.discount_label}
                    </span>
                    <h4 className="text-sm font-extrabold text-slate-900 mt-1">{coupon.business_name}</h4>
                    <p className="text-xs text-slate-600 line-clamp-1">{coupon.offer_title}</p>
                  </div>

                  <div className="bg-red-50/70 border border-red-200/80 rounded-xl p-3 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-slate-500 font-semibold block uppercase">Code</span>
                      <span className="font-mono text-base font-black text-[#C8102E] tracking-wider">
                        {coupon.coupon_code}
                      </span>
                    </div>
                    <button
                      onClick={() => handleCopyCode(coupon.coupon_code)}
                      className="p-2 bg-white hover:bg-slate-50 text-slate-700 rounded-lg border border-red-200 text-xs font-bold flex items-center gap-1 transition-colors"
                    >
                      {copiedCode === coupon.coupon_code ? (
                        <Check className="w-4 h-4 text-emerald-600" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>

                  <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100">
                    <span>Area: {coupon.business_area}</span>
                    <span>Till {new Date(coupon.valid_until).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* TAB 3: MYSTERY SCRATCH CARDS */}
      {activeTab === "scratch-cards" && (
        <section className="space-y-6">
          <div className="text-center max-w-lg mx-auto space-y-1">
            <h3 className="text-lg font-bold text-slate-900">Interactive Scratch & Win</h3>
            <p className="text-xs text-slate-500">
              Scratch off the silver card to unlock predetermined rewards generously sponsored by verified local businesses.
            </p>
          </div>

          {scratchCardPromos.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-3xl p-12 text-center space-y-3">
              <Gift className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="text-base font-bold text-slate-800">No active scratch cards right now</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Check back shortly! Local cafes and stores routinely release limited mystery scratch cards during civic events.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
              {scratchCardPromos.map((promo) => {
                const offer = promo.offers[0];
                return (
                  <ScratchCard
                    key={promo.campaign_id}
                    promotion={promo}
                    offer={offer}
                    onClaimed={() => setClaimedCoupons(getClaimedCoupons())}
                  />
                );
              })}
            </div>
          )}
        </section>
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
          onClaimed={() => setClaimedCoupons(getClaimedCoupons())}
        />
      )}
    </main>
  );
}
