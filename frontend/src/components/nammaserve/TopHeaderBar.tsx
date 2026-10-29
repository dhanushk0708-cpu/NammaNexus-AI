'use client';

import React, { useState } from "react";
import Link from "next/link";
import { Bell, ChevronDown, Sparkles, User, CheckCircle, Shield } from "lucide-react";

export default function TopHeaderBar() {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="bg-white border-b border-slate-200/90 sticky top-0 z-40 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Left Brand & Title */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5 text-xl font-extrabold text-slate-900 tracking-tight leading-none">
                <span>NammaServe</span>
                <span className="text-[#C8102E] font-black">AI</span>
              </div>
              <p className="text-[11px] text-slate-500 font-normal leading-tight mt-1">
                Every Service. Every Option. One Smart Dashboard.
              </p>
            </div>
          </Link>
        </div>

        {/* Right Navigation & Controls */}
        <div className="flex items-center gap-6">
          <nav className="hidden lg:flex items-center gap-5 text-xs font-semibold text-slate-600">
            <Link href="/" className="hover:text-slate-900 transition-colors">
              Home
            </Link>
            <Link href="/nammaserve" className="text-[#C8102E] font-bold">
              Services
            </Link>
            <button
              type="button"
              onClick={() => alert("Provider onboarding is available for verified Bengaluru vendors.")}
              className="hover:text-slate-900 transition-colors cursor-pointer"
            >
              For Providers
            </button>
            <Link href="/#pillars" className="hover:text-slate-900 transition-colors">
              About
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            {/* Notification Bell */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowNotifications(!showNotifications)}
                className="w-9 h-9 rounded-full border border-slate-200 flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors relative"
                aria-label="Notifications"
              >
                <Bell className="w-4 h-4" />
                <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-[#C8102E]" />
              </button>

              {showNotifications && (
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-lg border border-slate-200 p-3 text-xs z-50 space-y-2">
                  <div className="font-bold text-slate-900 pb-1 border-b border-slate-100 flex items-center justify-between">
                    <span>Civic Alerts</span>
                    <span className="text-[10px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded font-semibold">Live</span>
                  </div>
                  <div className="space-y-2 text-slate-600 text-[11px]">
                    <div className="p-2 bg-amber-50/70 rounded-lg border border-amber-200/60">
                      <p className="font-semibold text-amber-900">BWSSB Water Tanker Rates</p>
                      <p className="text-[10px] text-amber-700 mt-0.5">Verified standard rate card active for Kengeri & RR Nagar.</p>
                    </div>
                    <div className="p-2 bg-slate-50 rounded-lg border border-slate-200/60">
                      <p className="font-semibold text-slate-800">AC Servicing Peak Season</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">Booking 24h in advance is recommended for South Bengaluru.</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* User Profile Avatar Pill matching screenshot */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 pl-1 pr-2.5 py-1 rounded-full border border-slate-200 hover:border-slate-300 transition-colors bg-white shadow-2xs cursor-pointer"
              >
                <div className="w-7 h-7 rounded-full bg-[#E11D48] text-white flex items-center justify-center font-bold text-xs shadow-2xs">
                  D
                </div>
                <span className="text-xs font-semibold text-slate-800 hidden sm:inline">Dhanush</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-slate-200 p-2 text-xs z-50 space-y-1">
                  <div className="px-3 py-2 border-b border-slate-100">
                    <p className="font-bold text-slate-900">Dhanush</p>
                    <p className="text-[10px] text-slate-500">Citizen • Bengaluru South</p>
                  </div>
                  <Link
                    href="/spotfix"
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-[#C8102E]" />
                    <span>My SpotFix Reports</span>
                  </Link>
                  <div className="px-3 py-1.5 text-[10px] text-slate-400 flex items-center gap-1">
                    <Shield className="w-3 h-3 text-emerald-600" /> Supabase Auth Connected
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
