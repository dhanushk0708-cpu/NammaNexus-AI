'use client';

import React from "react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import type { ProviderItem } from "./NearbyProvidersList";

const InteractiveProviderMap = dynamic(() => import("./InteractiveProviderMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[480px] bg-slate-100 border border-slate-200/90 rounded-2xl flex flex-col items-center justify-center text-slate-500 text-xs gap-2">
      <Loader2 className="w-6 h-6 animate-spin text-[#C8102E]" />
      <span className="font-semibold text-slate-700">Loading NammaServe Interactive Map...</span>
      <span className="text-[11px] text-slate-400">OpenStreetMap Bengaluru Layer</span>
    </div>
  ),
});

interface NammaServeMapProps {
  centerLat: number;
  centerLng: number;
  providers: ProviderItem[];
  selectedProviderId: string | null;
  onSelectProvider: (provider: ProviderItem) => void;
}

export default function NammaServeMap(props: NammaServeMapProps) {
  return <InteractiveProviderMap {...props} />;
}
