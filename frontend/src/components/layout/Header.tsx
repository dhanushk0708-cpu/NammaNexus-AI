'use client';

import React from "react";
import Link from "next/link";
import { ShieldAlert, Sparkles, MapPin, Layers } from "lucide-react";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-slate-200 shadow-xs">
      {/* Top Karnataka Accent Ribbon */}
      <div className="h-1 w-full bg-gradient-to-r from-[#C8102E] via-[#FFC72C] to-[#C8102E]" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand Logo & Title */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#C8102E] to-[#990B22] text-white flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform">
            <ShieldAlert className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-bold text-slate-900 text-base leading-none tracking-tight">
              NammaNexus <span className="text-[#C8102E] text-xs px-1.5 py-0.5 rounded bg-red-50 border border-red-200">AI</span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium leading-tight mt-0.5">
              Bengaluru Civic Intelligence Platform
            </p>
          </div>
        </Link>

        {/* Navigation Bar */}
        <nav className="hidden md:flex items-center gap-1 text-xs font-semibold">
          <Link
            href="/"
            className="px-3 py-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            Platform Hub
          </Link>
          <Link
            href="/spotfix"
            className="px-3 py-2 rounded-lg bg-red-50 text-[#C8102E] border border-red-200/80 font-bold flex items-center gap-1.5 shadow-2xs hover:bg-red-100/80 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            SpotFix AI
          </Link>
          <Link
            href="/nammaserve"
            className="px-3 py-2 rounded-lg text-slate-700 hover:text-[#C8102E] hover:bg-red-50/60 font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-amber-600" />
            NammaServe
          </Link>
          <span className="px-3 py-2 text-slate-400 cursor-not-allowed flex items-center gap-1">
            CivicVoice
          </span>
          <span className="px-[#10px] text-slate-300">|</span>
          <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200/80 px-2.5 py-1 rounded-full flex items-center gap-1">
            <MapPin className="w-3 h-3 text-[#C8102E]" /> BBMP & BWSSB
          </span>
        </nav>

        {/* Mobile Links */}
        <div className="md:hidden flex items-center gap-2">
          <Link
            href="/nammaserve"
            className="text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800 px-2.5 py-1.5 rounded-lg border border-slate-200"
          >
            NammaServe
          </Link>
          <Link
            href="/spotfix"
            className="text-xs font-bold bg-[#C8102E] text-white px-3 py-1.5 rounded-lg flex items-center gap-1 shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            SpotFix
          </Link>
        </div>
      </div>
    </header>
  );
}
