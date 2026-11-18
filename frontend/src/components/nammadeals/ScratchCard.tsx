'use client';

import React, { useRef, useState, useEffect } from "react";
import { Sparkles, Gift, Check, Copy, ArrowRight, ShieldCheck } from "lucide-react";
import { PromotionItem, PromotionOfferItem, saveClaimedCoupon } from "@/lib/nammadealsApi";

interface ScratchCardProps {
  promotion: PromotionItem;
  offer: PromotionOfferItem;
  onClaimed?: () => void;
}

export default function ScratchCard({ promotion, offer, onClaimed }: ScratchCardProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isRevealed, setIsRevealed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isDrawing, setIsDrawing] = useState(false);

  // Initialize canvas with silver/metallic overlay
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || isRevealed) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Fill with metallic silver gradient
    const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    grad.addColorStop(0, "#D1D5DB");
    grad.addColorStop(0.5, "#9CA3AF");
    grad.addColorStop(1, "#6B7280");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Text on silver foil
    ctx.font = "bold 15px sans-serif";
    ctx.fillStyle = "#374151";
    ctx.textAlign = "center";
    ctx.fillText("✨ SCRATCH HERE ✨", canvas.width / 2, canvas.height / 2 - 8);
    ctx.font = "12px sans-serif";
    ctx.fillStyle = "#4B5563";
    ctx.fillText("to reveal your civic reward", canvas.width / 2, canvas.height / 2 + 16);
  }, [isRevealed]);

  const scratch = (clientX: number, clientY: number) => {
    const canvas = canvasRef.current;
    if (!canvas || isRevealed) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(x, y, 22, 0, Math.PI * 2);
    ctx.fill();

    checkScratchedPercentage(ctx, canvas);
  };

  const checkScratchedPercentage = (ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement) => {
    try {
      const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      let clearedPixels = 0;
      for (let i = 3; i < imgData.data.length; i += 16) {
        if (imgData.data[i] === 0) clearedPixels++;
      }
      const totalSampled = imgData.data.length / 16;
      if (clearedPixels / totalSampled > 0.45) {
        revealReward();
      }
    } catch {
      // In case of any browser security restriction
    }
  };

  const revealReward = () => {
    setIsRevealed(true);
    if (offer.coupon_code) {
      saveClaimedCoupon({
        id: `${offer.id}_scratch_${Date.now()}`,
        campaign_id: promotion.campaign_id,
        campaign_name: promotion.campaign_name,
        business_name: promotion.business_name,
        business_area: promotion.business_area,
        offer_title: offer.title,
        coupon_code: offer.coupon_code,
        discount_label:
          offer.discount_type === "PERCENTAGE"
            ? `${offer.discount_value}% OFF`
            : offer.discount_type === "FLAT"
            ? `₹${offer.discount_value} OFF`
            : "SECRET REWARD",
        valid_until: offer.valid_until,
        claimed_at: new Date().toISOString(),
        is_used: false,
      });
      if (onClaimed) onClaimed();
    }
  };

  const handleCopy = () => {
    if (offer.coupon_code) {
      navigator.clipboard.writeText(offer.coupon_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 space-y-4 text-center max-w-sm mx-auto overflow-hidden">
      <div className="space-y-1">
        <span className="text-[10px] font-bold tracking-wider uppercase text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full inline-flex items-center gap-1">
          <Gift className="w-3 h-3 text-amber-600" />
          Mystery Civic Scratch Card
        </span>
        <h3 className="text-base font-extrabold text-slate-900">{promotion.business_name}</h3>
        <p className="text-xs text-slate-500">{promotion.business_area}</p>
      </div>

      {/* Scratch Container */}
      <div className="relative w-full h-44 rounded-2xl overflow-hidden border-2 border-dashed border-red-200 flex items-center justify-center bg-gradient-to-br from-red-50 to-amber-50">
        {/* Underlying Predetermined Backend Reward */}
        <div className="p-4 space-y-2 text-center w-full">
          <div className="text-xs font-bold text-amber-700 bg-amber-100/90 py-0.5 px-2 rounded-md inline-block">
            {offer.scratch_card_config?.win_headline || offer.title}
          </div>
          <div className="font-mono text-2xl font-black text-[#C8102E] tracking-widest">
            {offer.coupon_code || "REWARD50"}
          </div>
          <p className="text-[11px] text-slate-600 font-medium">
            Valid till {new Date(offer.valid_until).toLocaleDateString()}
          </p>
        </div>

        {/* Scratch Canvas Overlay */}
        {!isRevealed && (
          <canvas
            ref={canvasRef}
            width={320}
            height={176}
            onMouseDown={() => setIsDrawing(true)}
            onMouseUp={() => setIsDrawing(false)}
            onMouseLeave={() => setIsDrawing(false)}
            onMouseMove={(e) => {
              if (isDrawing) scratch(e.clientX, e.clientY);
            }}
            onTouchStart={() => setIsDrawing(true)}
            onTouchEnd={() => setIsDrawing(false)}
            onTouchMove={(e) => {
              if (e.touches[0]) scratch(e.touches[0].clientX, e.touches[0].clientY);
            }}
            className="absolute inset-0 w-full h-full cursor-pointer z-10 touch-none"
          />
        )}
      </div>

      {/* Interactive Controls */}
      {!isRevealed ? (
        <button
          onClick={revealReward}
          className="w-full text-xs font-bold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 py-2 rounded-xl border border-slate-200 transition-colors flex items-center justify-center gap-1.5"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>Click to Reveal Automatically</span>
        </button>
      ) : (
        <div className="space-y-2 pt-1 animate-in fade-in duration-300">
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-2 text-xs text-emerald-800 font-semibold flex items-center justify-center gap-1.5">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>Reward Unlocked & Saved to My Coupons!</span>
          </div>
          <button
            onClick={handleCopy}
            className="w-full bg-[#C8102E] hover:bg-[#A60C24] text-white py-2.5 rounded-xl font-bold text-xs shadow-sm flex items-center justify-center gap-1.5 transition-all"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-300" /> : <Copy className="w-4 h-4" />}
            <span>{copied ? "Copied Coupon Code" : "Copy Coupon Code"}</span>
          </button>
        </div>
      )}
    </div>
  );
}
