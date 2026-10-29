'use client';

import React from "react";
import Link from "next/link";
import {
  Search,
  Calendar,
  Bookmark,
  Star,
  AlertTriangle,
  Store,
  Settings,
} from "lucide-react";
import VidhanaSoudhaIllustration from "./VidhanaSoudhaIllustration";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const menuItems = [
    { id: "search", label: "Search Services", icon: Search, href: "#", isRoute: false },
    { id: "bookings", label: "My Bookings", icon: Calendar, href: "#", isRoute: false },
    { id: "saved", label: "Saved Providers", icon: Bookmark, href: "#", isRoute: false },
    { id: "reviews", label: "User Reviews", icon: Star, href: "#", isRoute: false },
    { id: "report", label: "Report an Issue", icon: AlertTriangle, href: "/spotfix", isRoute: true },
    { id: "providers", label: "For Providers", icon: Store, href: "#", isRoute: false },
    { id: "admin", label: "Admin Dashboard", icon: Settings, href: "#", isRoute: false },
  ];

  return (
    <aside className="w-56 shrink-0 bg-white border-r border-slate-200/90 flex flex-col min-h-[calc(100vh-4rem)] select-none">
      {/* Top Vidhana Soudha City Silhouette */}
      <div className="pt-4 pb-2 px-3 border-b border-slate-100 bg-gradient-to-b from-amber-50/50 to-white">
        <VidhanaSoudhaIllustration className="w-full h-14" />
      </div>

      {/* Navigation Menu */}
      <nav className="p-3 space-y-1 flex-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          if (item.isRoute) {
            return (
              <Link
                key={item.id}
                href={item.href}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium text-slate-700 hover:bg-red-50 hover:text-[#C8102E] transition-colors group"
              >
                <Icon className="w-4 h-4 text-slate-500 group-hover:text-[#C8102E] transition-colors" />
                <span>{item.label}</span>
              </Link>
            );
          }

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all text-left ${
                isActive
                  ? "bg-[#FEF3C7] text-slate-900 shadow-2xs border-l-4 border-[#C8102E] font-bold"
                  : "text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
              }`}
            >
              <Icon
                className={`w-4 h-4 ${
                  isActive ? "text-[#C8102E]" : "text-slate-400 group-hover:text-slate-600"
                }`}
              />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer Branding Info */}
      <div className="p-4 border-t border-slate-100 text-[10px] text-slate-400 space-y-1">
        <p className="font-semibold text-slate-600">NammaServe AI • v1.0</p>
        <p>Bengaluru Public Utilities & Local Services</p>
      </div>
    </aside>
  );
}
