'use client';

import React from "react";
import {
  Users,
  Tag,
  ShieldCheck,
  Calendar,
  Star,
  Lightbulb,
  ExternalLink,
  MapPin,
} from "lucide-react";

interface WhyPlatformsCardProps {
  serviceName: string;
  locality: string;
}

export default function WhyPlatformsCard({
  serviceName,
  locality,
}: WhyPlatformsCardProps) {
  const googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    `${serviceName} near ${locality} Bengaluru`
  )}`;

  const benefits = [
    { icon: Users, text: "Wide range of options", color: "text-amber-500" },
    { icon: Tag, text: "Compare prices easily", color: "text-amber-500" },
    { icon: ShieldCheck, text: "Verified professionals", color: "text-emerald-500" },
    { icon: Calendar, text: "Online booking", color: "text-red-500" },
    { icon: Star, text: "Ratings and reviews", color: "text-amber-500" },
  ];

  return (
    <div className="w-full bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 shadow-2xs space-y-4">
      {/* Title */}
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-extrabold text-slate-900">
          Why Use Platforms?
        </h3>
      </div>

      {/* Benefits List matching screenshot */}
      <div className="space-y-2.5 text-xs text-slate-700">
        {benefits.map((b, idx) => {
          const Icon = b.icon;
          return (
            <div key={idx} className="flex items-center gap-2.5">
              <Icon className={`w-4 h-4 shrink-0 ${b.color}`} />
              <span className="font-medium text-slate-700">{b.text}</span>
            </div>
          );
        })}
      </div>

      {/* External Google Maps Explorer Box matching screenshot */}
      <div className="p-3.5 bg-amber-50/70 border border-amber-200/80 rounded-xl space-y-2.5">
        <div className="flex items-start gap-2.5">
          <Lightbulb className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-700 leading-snug">
            You can also explore <strong className="font-extrabold text-slate-900">Google Maps</strong> for more nearby options.
          </p>
        </div>

        <a
          href={googleMapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 font-bold text-xs py-2 px-3 rounded-xl shadow-2xs transition-colors flex items-center justify-center gap-2 group cursor-pointer"
        >
          <MapPin className="w-3.5 h-3.5 text-[#C8102E]" />
          <span>Open Google Maps</span>
          <ExternalLink className="w-3 h-3 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
        </a>
      </div>
    </div>
  );
}
