'use client';

import React from "react";
import { ShieldCheck, Heart, MapPin } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto text-slate-600 text-xs">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm mb-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#C8102E]" />
            NammaNexus AI
          </div>
          <p className="text-slate-500 leading-relaxed">
            AI-Powered Civic Intelligence Platform for Bengaluru. Empowering citizens with automated verification, authority routing, and social accountability.
          </p>
        </div>

        <div>
          <h4 className="font-bold text-slate-900 mb-2 uppercase text-[11px] tracking-wider text-slate-700">
            Platform Pillars
          </h4>
          <ul className="space-y-1.5 text-slate-500">
            <li className="text-[#C8102E] font-semibold">1. SpotFix AI (Active Intake)</li>
            <li>2. NammaServe AI (Public Utilities)</li>
            <li>3. CivicVoice AI (Community Sentiment)</li>
            <li>4. SafeStreet AI (Urban Safety)</li>
            <li>5. CivicAssist AI (Citizen Assistant)</li>
          </ul>
        </div>

        <div>
          <h4 className="font-bold text-slate-900 mb-2 uppercase text-[11px] tracking-wider text-slate-700">
            Civic Transparency
          </h4>
          <p className="text-slate-500 leading-relaxed">
            SpotFix issues are routed deterministically to official authorities (BBMP, BWSSB, BESCOM) based on PostGIS spatial boundaries and verified by Gemini Vision AI.
          </p>
          <div className="mt-3 flex items-center gap-1.5 text-[11px] font-semibold text-slate-700">
            <ShieldCheck className="w-4 h-4 text-emerald-600" /> Human Approval & Privacy Guaranteed
          </div>
        </div>
      </div>

      <div className="border-t border-slate-100 py-4 bg-slate-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-slate-400 text-[11px]">
          <div className="flex items-center gap-1">
            <span>Built with</span>
            <Heart className="w-3 h-3 text-[#C8102E] fill-[#C8102E]" />
            <span>for Bengaluru, Karnataka</span>
          </div>
          <div>© {new Date().getFullYear()} NammaNexus AI. Final-Year Civic Technology Project.</div>
        </div>
      </div>
    </footer>
  );
}
