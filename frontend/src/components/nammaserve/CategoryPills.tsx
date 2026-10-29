'use client';

import React from "react";
import {
  Snowflake,
  Sparkles,
  Wrench,
  Zap,
  Paintbrush,
  Bug,
  Truck,
  Package,
  Recycle,
  LayoutGrid,
} from "lucide-react";

interface CategoryPillsProps {
  selectedCategory: string;
  onSelectCategory: (categorySlug: string, categoryName: string) => void;
}

export interface CategoryItem {
  slug: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
}

export const CATEGORIES: CategoryItem[] = [
  { slug: "ac-repair", name: "AC Repair", icon: Snowflake, colorClass: "text-blue-500" },
  { slug: "home-cleaning", name: "Home Cleaning", icon: Sparkles, colorClass: "text-amber-500" },
  { slug: "plumbing", name: "Plumbing", icon: Wrench, colorClass: "text-sky-600" },
  { slug: "electrical", name: "Electrical", icon: Zap, colorClass: "text-amber-600" },
  { slug: "painting", name: "Painting", icon: Paintbrush, colorClass: "text-red-500" },
  { slug: "pest-control", name: "Pest Control", icon: Bug, colorClass: "text-rose-600" },
  { slug: "water-tanker", name: "Water Tanker", icon: Truck, colorClass: "text-cyan-600" },
  { slug: "packers-movers", name: "Packers & Movers", icon: Package, colorClass: "text-amber-700" },
  { slug: "e-waste", name: "E-Waste", icon: Recycle, colorClass: "text-emerald-600" },
  { slug: "more", name: "More", icon: LayoutGrid, colorClass: "text-slate-600" },
];

export default function CategoryPills({
  selectedCategory,
  onSelectCategory,
}: CategoryPillsProps) {
  return (
    <div className="w-full overflow-x-auto pb-1 scrollbar-none">
      <div className="flex items-center gap-2.5 min-w-max">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isSelected =
            selectedCategory.toLowerCase() === cat.slug.toLowerCase() ||
            selectedCategory.toLowerCase() === cat.name.toLowerCase();

          return (
            <button
              key={cat.slug}
              type="button"
              onClick={() => onSelectCategory(cat.slug, cat.name)}
              className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer select-none ${
                isSelected
                  ? "bg-amber-50/90 border-amber-400 text-slate-900 shadow-xs ring-1 ring-amber-300 font-bold"
                  : "bg-white border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50 shadow-2xs"
              }`}
            >
              <Icon
                className={`w-4 h-4 ${
                  isSelected ? "text-amber-600 scale-110" : cat.colorClass
                } transition-transform`}
              />
              <span>{cat.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
