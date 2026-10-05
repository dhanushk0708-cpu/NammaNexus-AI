'use client';

import React from "react";
import Link from "next/link";
import {
  Sparkles,
  Camera,
  MapPin,
  ShieldCheck,
  CheckCircle2,
  Share2,
  Building2,
  Activity,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";

export default function Home() {
  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 space-y-12 flex-1">
      {/* Hero Header Section */}
      <section className="bg-white border border-slate-200 rounded-3xl p-8 sm:p-12 shadow-xs relative overflow-hidden">
        {/* Subtle Karnataka Flag Accent Edge */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#C8102E] via-[#FFC72C] to-[#C8102E]" />

        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 bg-red-50 border border-red-200/80 px-3 py-1 rounded-full text-xs font-bold text-[#C8102E] uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            NammaNexus AI Civic Intelligence
          </div>

          <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-tight">
            Smarter Civic Action for <span className="text-[#C8102E]">Bengaluru</span>.
          </h1>

          <p className="text-base sm:text-lg text-slate-600 leading-relaxed font-normal">
            Report civic issues instantly. Verified by AI vision, scored for predictive urban impact, routed deterministically to civic authorities (BBMP, BWSSB, BESCOM), and published for social awareness.
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <Link
              href="/spotfix"
              className="inline-flex items-center justify-center gap-2 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold px-6 py-3.5 rounded-xl shadow-md transition-all text-sm group"
            >
              <Camera className="w-4 h-4 text-amber-300" />
              <span>Launch SpotFix AI Intake</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>

            <a
              href="#pillars"
              className="inline-flex items-center justify-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-5 py-3.5 rounded-xl border border-slate-200 transition-colors text-sm"
            >
              Explore Platform Pillars
            </a>
          </div>
        </div>
      </section>

      {/* Featured Pillar: SpotFix AI Card */}
      <section className="bg-gradient-to-br from-red-50/50 via-white to-amber-50/30 border border-red-200/80 rounded-2xl p-6 sm:p-8 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-red-100 pb-4">
          <div>
            <span className="text-xs font-bold text-[#C8102E] uppercase tracking-wider bg-red-100/80 px-2.5 py-0.5 rounded-md">
              Pillar 1 • Active Demonstration
            </span>
            <h2 className="text-2xl font-extrabold text-slate-900 mt-1 flex items-center gap-2">
              SpotFix AI
              <span className="text-xs bg-amber-100 text-amber-800 border border-amber-300 font-semibold px-2 py-0.5 rounded-full">
                Live Local Service
              </span>
            </h2>
          </div>
          <Link
            href="/spotfix"
            className="bg-[#C8102E] text-white hover:bg-[#A60C24] font-bold text-xs px-4 py-2.5 rounded-lg flex items-center gap-1.5 shadow-2xs transition-colors"
          >
            Start SpotFix Intake <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
          <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-1.5 shadow-2xs">
            <div className="w-8 h-8 rounded-lg bg-red-50 text-[#C8102E] flex items-center justify-center font-bold">
              1
            </div>
            <h3 className="font-bold text-slate-900">Photo & Location Intake</h3>
            <p className="text-slate-500 leading-relaxed">
              Upload pothole, garbage, or waterlogging photo with live coordinates.
            </p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-1.5 shadow-2xs">
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
              2
            </div>
            <h3 className="font-bold text-slate-900">AI Verification</h3>
            <p className="text-slate-500 leading-relaxed">
              Gemini Vision classifies category, severity, and visual explanation.
            </p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-1.5 shadow-2xs">
            <div className="w-8 h-8 rounded-lg bg-[#C8102E]/10 text-[#C8102E] flex items-center justify-center font-bold">
              3
            </div>
            <h3 className="font-bold text-slate-900">Impact & Routing</h3>
            <p className="text-slate-500 leading-relaxed">
              Scores 0-100 urban risk & routes to BBMP, BWSSB, or BESCOM.
            </p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-1.5 shadow-2xs">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
              4
            </div>
            <h3 className="font-bold text-slate-900">Official Submission</h3>
            <p className="text-slate-500 leading-relaxed">
              Citizen approves draft $\rightarrow$ email sent to authority + Instagram published.
            </p>
          </div>
        </div>
      </section>

      {/* 5 Platform Pillars Grid */}
      <section id="pillars" className="space-y-6">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900">
            NammaNexus AI Platform Architecture
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Five modular civic intelligence pillars sharing unified spatial & authority data.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-2xl border-2 border-red-200 shadow-xs relative">
            <span className="text-[10px] font-bold text-[#C8102E] uppercase bg-red-50 border border-red-200 px-2 py-0.5 rounded">
              Pillar 1 • Ready
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-2">SpotFix AI</h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Automated civic issue verification, predictive impact assessment, and social awareness dispatch.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs opacity-80">
            <span className="text-[10px] font-bold text-slate-500 uppercase bg-slate-100 px-2 py-0.5 rounded">
              Pillar 2 • Modular
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-2">NammaServe AI</h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Public utilities intelligence tracking water, power, and road maintenance schedules.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs opacity-80">
            <span className="text-[10px] font-bold text-slate-500 uppercase bg-slate-100 px-2 py-0.5 rounded">
              Pillar 3 • Modular
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-2">CivicVoice AI</h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Neighborhood sentiment analysis and community grievance theme extraction.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs opacity-80">
            <span className="text-[10px] font-bold text-slate-500 uppercase bg-slate-100 px-2 py-0.5 rounded">
              Pillar 4 • Modular
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-2">SafeStreet AI</h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Urban street safety hazard modeling and pedestrian risk mapping.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs opacity-80">
            <span className="text-[10px] font-bold text-slate-500 uppercase bg-slate-100 px-2 py-0.5 rounded">
              Pillar 5 • Modular
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-2">CivicAssist AI</h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Interactive citizen assistant providing evidence-grounded civic guidance.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
