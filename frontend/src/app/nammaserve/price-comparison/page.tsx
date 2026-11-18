'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import {
  Search,
  Layers,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Info,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Sparkles,
  HelpCircle,
  Building,
  Tag,
  Scale,
  MapPin,
  Clock,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface PriceRecord {
  id: string;
  record_hash: string;
  source_platform: string;
  service_category: string;
  service_name: string;
  provider_name: string;
  published_price: string;
  currency: string;
  price_type: string;
  price_unit: string | null;
  price_scope: string | null;
  geographic_scope: string;
  source_url: string;
  source_checked_date: string;
  verification_status: string;
  notes: string | null;
  price_min: number | null;
  price_max: number | null;
  is_locality_specific: boolean;
  created_at: string;
}

interface OverviewStats {
  total_records: number;
  platforms_count: Record<string, number>;
  categories_count: Record<string, number>;
  price_types_count: Record<string, number>;
  verification_breakdown: Record<string, number>;
  citywide_confirmed_count: number;
  locality_specific_count: number;
  latest_research_date: string;
  disclaimer: string;
}

interface BenchmarkItem {
  category: string;
  benchmark_task: string;
  urban_company: PriceRecord | null;
  nobroker: PriceRecord | null;
  justdial: PriceRecord | null;
  sulekha: PriceRecord | null;
  comparability_notes: string | null;
}

export default function PriceComparisonPage() {
  // Data States
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [records, setRecords] = useState<PriceRecord[]>([]);
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [benchmarks, setBenchmarks] = useState<BenchmarkItem[]>([]);
  const [selectedBenchmarkCat, setSelectedBenchmarkCat] = useState<string>('All');

  // Filter States
  const [search, setSearch] = useState<string>('');
  const [category, setCategory] = useState<string>('All');
  const [platform, setPlatform] = useState<string>('All');
  const [priceType, setPriceType] = useState<string>('All');
  const [scopeFilter, setScopeFilter] = useState<string>('All');
  const [verStatus, setVerStatus] = useState<string>('All');
  const [sortBy, setSortBy] = useState<string>('service_name');
  const [sortDir, setSortDir] = useState<string>('asc');
  const [page, setPage] = useState<number>(1);
  const limit = 20;

  // UI States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'benchmarks' | 'catalogue'>('benchmarks');

  // Fetch Overview Stats
  useEffect(() => {
    async function fetchOverview() {
      try {
        const res = await fetch(`${API_BASE}/nammaserve/price-comparison/overview`);
        if (res.ok) {
          const data = await res.json();
          setOverview(data);
        }
      } catch (err) {
        console.error('Failed to load price comparison overview:', err);
      }
    }
    fetchOverview();
  }, []);

  // Fetch Benchmarks
  useEffect(() => {
    async function fetchBenchmarks() {
      try {
        const url = selectedBenchmarkCat === 'All'
          ? `${API_BASE}/nammaserve/price-comparison/benchmarks`
          : `${API_BASE}/nammaserve/price-comparison/benchmarks?category=${encodeURIComponent(selectedBenchmarkCat)}`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setBenchmarks(data.benchmarks || []);
        }
      } catch (err) {
        console.error('Failed to load benchmarks:', err);
      }
    }
    fetchBenchmarks();
  }, [selectedBenchmarkCat]);

  // Fetch Filtered & Paginated Records with Debounce and AbortController
  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (category !== 'All') params.append('category', category);
        if (platform !== 'All') params.append('platform', platform);
        if (priceType !== 'All') params.append('price_type', priceType);
        if (verStatus !== 'All') params.append('verification_status', verStatus);
        if (scopeFilter === 'locality_only') params.append('locality_specific_only', 'true');
        if (scopeFilter === 'citywide_only') params.append('locality_specific_only', 'false');
        if (search.trim()) params.append('search', search.trim());

        params.append('sort_by', sortBy);
        params.append('sort_dir', sortDir);
        params.append('page', page.toString());
        params.append('limit', limit.toString());

        const res = await fetch(`${API_BASE}/nammaserve/price-comparison/records?${params.toString()}`, {
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!ignore) {
          setRecords(data.items || []);
          setTotalRecords(data.total || 0);
          setTotalPages(data.pages || 1);
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        console.error('Failed to load comparison records:', err);
        if (!ignore) {
          setError('Unable to load comparison records from the backend.');
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }, search.trim() ? 300 : 0);

    return () => {
      ignore = true;
      controller.abort();
      clearTimeout(timer);
    };
  }, [category, platform, priceType, scopeFilter, verStatus, search, sortBy, sortDir, page]);

  const resetFilters = () => {
    setSearch('');
    setCategory('All');
    setPlatform('All');
    setPriceType('All');
    setScopeFilter('All');
    setVerStatus('All');
    setSortBy('service_name');
    setSortDir('asc');
    setPage(1);
  };

  // Helper for rendering price tag strictly conforming to guidelines
  const renderPriceBadge = (record: PriceRecord) => {
    const pt = record.price_type;
    const pStr = record.published_price;

    if (pt === 'QUOTATION_REQUIRED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
          <HelpCircle className="w-3 h-3" /> Quote required
        </span>
      );
    }
    if (pt === 'UNPUBLISHED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
          Price not published
        </span>
      );
    }
    if (pt === 'STARTING_FROM') {
      return (
        <div className="flex flex-col">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold bg-amber-50 text-amber-800 border border-amber-300">
            From ₹{pStr}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5">Starting rate; final quote varies</span>
        </div>
      );
    }
    if (pt === 'PRICE_RANGE') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold bg-blue-50 text-blue-800 border border-blue-200">
          ₹{pStr}
        </span>
      );
    }
    // FIXED
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-300">
        ₹{pStr} fixed
      </span>
    );
  };

  const getPlatformColor = (plat: string) => {
    switch (plat) {
      case 'Urban Company':
        return 'bg-slate-900 text-white';
      case 'NoBroker':
        return 'bg-[#C8102E] text-white';
      case 'Justdial':
        return 'bg-orange-500 text-white';
      case 'Sulekha':
        return 'bg-blue-600 text-white';
      default:
        return 'bg-slate-700 text-white';
    }
  };

  const categoriesList = [
    'All',
    'Plumbing',
    'AC repair and servicing',
    'Electrical services',
    'House cleaning',
    'Pest control',
    'Appliance repair',
    'Water purifier/RO services',
    'Carpentry',
  ];

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      {/* Top Experience Sub-Navigation Ribbon */}
      <div className="bg-white border-b border-slate-200 sticky top-16 z-40 px-4 sm:px-6 py-2 shadow-2xs">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs font-medium">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-700 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-amber-600" /> NammaServe Pillar:
            </span>
            <Link
              href="/nammaserve"
              className="px-2.5 py-1 rounded-md text-slate-600 hover:text-[#C8102E] hover:bg-red-50 transition-colors"
            >
              Marketplace Discovery
            </Link>
            <span className="text-slate-300">|</span>
            <Link
              href="/nammaserve/research-compare"
              className="px-2.5 py-1 rounded-md text-slate-600 hover:text-[#C8102E] hover:bg-red-50 transition-colors"
            >
              Provider Research Dashboard (128 Candidates)
            </Link>
            <span className="text-slate-300">|</span>
            <span className="px-2.5 py-1 rounded-md bg-red-50 text-[#C8102E] font-bold border border-red-200">
              Bengaluru Price Comparison (142 Records)
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-500">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>Dataset Snapshot: <strong>29 Oct 2026</strong></span>
          </div>
        </div>
      </div>

      {/* Main Header / Hero */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 pt-8 pb-10 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-red-50 border border-red-200 text-[#C8102E] text-xs font-bold mb-2">
                <Scale className="w-3.5 h-3.5 text-amber-500" /> Cross-Platform Market Intelligence
              </div>
              <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                Bengaluru Home Services <span className="text-[#C8102E]">Price Comparison</span>
              </h1>
              <p className="text-sm sm:text-base text-slate-600 max-w-3xl mt-1 leading-relaxed">
                Centralized price transparency across Urban Company, NoBroker, Justdial, and Sulekha.
                Compare rate cards, identify benchmark prices, and review documented caveats for Bengaluru.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('benchmarks')}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'benchmarks'
                    ? 'bg-[#C8102E] text-white shadow-sm'
                    : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
                }`}
              >
                <Scale className="w-4 h-4" /> Benchmark Matrix
              </button>
              <button
                onClick={() => setActiveTab('catalogue')}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeTab === 'catalogue'
                    ? 'bg-[#C8102E] text-white shadow-sm'
                    : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
                }`}
              >
                <Tag className="w-4 h-4" /> Full Catalog ({totalRecords || 142})
              </button>
            </div>
          </div>

          {/* Mandatory Research Disclaimer Notice */}
          <div className="bg-amber-50 border border-amber-300 rounded-xl p-3.5 sm:p-4 text-xs text-amber-950 flex items-start gap-3 shadow-2xs">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold text-amber-900">
                Notice: Research Snapshot — Not Live Pricing
              </p>
              <p className="text-amber-800 leading-relaxed">
                Prices are research snapshots dated <strong>29 October 2026</strong>, not live quotes.
                Final costs may vary by locality, job scope, materials, spare parts, access, and provider assessment.
                Do not treat starting prices as final quotes, and confirm exact scope before availing services.
              </p>
            </div>
          </div>

          {/* KPI Stat Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Records</div>
              <div className="text-2xl font-black text-slate-900 mt-1">142</div>
              <div className="text-[11px] text-emerald-600 font-medium mt-0.5">100% Sourced</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Urban Company</div>
              <div className="text-2xl font-black text-slate-900 mt-1">52</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Platform Standard</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">NoBroker</div>
              <div className="text-2xl font-black text-slate-900 mt-1">51</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Platform Rate Card</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Justdial</div>
              <div className="text-2xl font-black text-slate-900 mt-1">20</div>
              <div className="text-[11px] text-amber-600 font-medium mt-0.5">Vendor Listings</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Sulekha</div>
              <div className="text-2xl font-black text-slate-900 mt-1">19</div>
              <div className="text-[11px] text-blue-600 font-medium mt-0.5">Cost Guide Tables</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Locality Caveats</div>
              <div className="text-2xl font-black text-amber-700 mt-1">33</div>
              <div className="text-[11px] text-amber-600 font-medium mt-0.5">Area Specific / Flagged</div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* VIEW 1: Cross-Platform Benchmark Matrix */}
        {activeTab === 'benchmarks' && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Scale className="w-5 h-5 text-[#C8102E]" /> Cross-Platform Comparable Benchmarks
                </h2>
                <p className="text-xs text-slate-600 mt-0.5">
                  Direct equivalent tasks compared side-by-side using official Bengaluru rate pages.
                </p>
              </div>

              {/* Category Filter Pills */}
              <div className="flex flex-wrap gap-1.5">
                {['All', 'Plumbing', 'AC Repair & Servicing', 'Electrical Services', 'House Cleaning', 'Appliance Repair', 'Water Purifier / RO Services', 'Carpentry'].map((c) => (
                  <button
                    key={c}
                    onClick={() => setSelectedBenchmarkCat(c === 'All' ? 'All' : c)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                      (selectedBenchmarkCat === 'All' && c === 'All') || selectedBenchmarkCat === c
                        ? 'bg-[#C8102E] text-white shadow-2xs'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>

            {/* Benchmarks Grid */}
            <div className="grid grid-cols-1 gap-4">
              {benchmarks.map((bm, idx) => (
                <div
                  key={idx}
                  className="bg-white rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all overflow-hidden"
                >
                  <div className="bg-slate-50 border-b border-slate-200 px-5 py-3 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="px-2 py-0.5 rounded bg-red-50 text-[#C8102E] text-[11px] font-bold border border-red-200">
                        {bm.category}
                      </span>
                      <h3 className="font-bold text-slate-900 text-sm sm:text-base">
                        {bm.benchmark_task}
                      </h3>
                    </div>
                    {bm.comparability_notes && (
                      <span className="text-xs text-slate-500 italic max-w-md truncate">
                        Scope: {bm.comparability_notes}
                      </span>
                    )}
                  </div>

                  <div className="p-4 sm:p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Urban Company Column */}
                    <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 text-white">
                            Urban Company
                          </span>
                          <span className="text-[10px] text-slate-400">Standardized</span>
                        </div>
                        {bm.urban_company ? (
                          <div className="space-y-1.5">
                            <div className="font-semibold text-xs text-slate-800 line-clamp-2">
                              {bm.urban_company.service_name}
                            </div>
                            <div>{renderPriceBadge(bm.urban_company)}</div>
                            <div className="text-[11px] text-slate-500">
                              Unit: {bm.urban_company.price_unit || 'per unit'}
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs text-slate-400 italic py-2">
                            No comparable published price
                          </div>
                        )}
                      </div>
                      {bm.urban_company && (
                        <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between text-[11px]">
                          <span className="text-emerald-700 font-medium">Citywide</span>
                          <a
                            href={bm.urban_company.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#C8102E] hover:underline flex items-center gap-0.5"
                          >
                            Source <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      )}
                    </div>

                    {/* NoBroker Column */}
                    <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#C8102E] text-white">
                            NoBroker
                          </span>
                          <span className="text-[10px] text-slate-400">Rate Card</span>
                        </div>
                        {bm.nobroker ? (
                          <div className="space-y-1.5">
                            <div className="font-semibold text-xs text-slate-800 line-clamp-2">
                              {bm.nobroker.service_name}
                            </div>
                            <div>{renderPriceBadge(bm.nobroker)}</div>
                            <div className="text-[11px] text-slate-500">
                              Unit: {bm.nobroker.price_unit || 'per unit'}
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs text-slate-400 italic py-2">
                            No comparable published price
                          </div>
                        )}
                      </div>
                      {bm.nobroker && (
                        <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between text-[11px]">
                          <span className="text-emerald-700 font-medium">Citywide</span>
                          <a
                            href={bm.nobroker.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#C8102E] hover:underline flex items-center gap-0.5"
                          >
                            Source <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      )}
                    </div>

                    {/* Justdial Column */}
                    <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-500 text-white">
                            Justdial
                          </span>
                          <span className="text-[10px] text-amber-600 font-medium">Vendor Listing</span>
                        </div>
                        {bm.justdial ? (
                          <div className="space-y-1.5">
                            <div className="font-semibold text-xs text-slate-800 line-clamp-2">
                              {bm.justdial.service_name}
                            </div>
                            <div>{renderPriceBadge(bm.justdial)}</div>
                            <div className="text-[11px] text-slate-500">
                              Vendor: {bm.justdial.provider_name}
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs text-slate-400 italic py-2">
                            No comparable published price
                          </div>
                        )}
                      </div>
                      {bm.justdial && (
                        <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between text-[11px]">
                          {bm.justdial.is_locality_specific ? (
                            <span className="text-amber-700 font-medium">Locality Specific</span>
                          ) : (
                            <span className="text-emerald-700 font-medium">Citywide</span>
                          )}
                          <a
                            href={bm.justdial.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#C8102E] hover:underline flex items-center gap-0.5"
                          >
                            Source <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      )}
                    </div>

                    {/* Sulekha Column */}
                    <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-600 text-white">
                            Sulekha
                          </span>
                          <span className="text-[10px] text-blue-600 font-medium">Cost Guide</span>
                        </div>
                        {bm.sulekha ? (
                          <div className="space-y-1.5">
                            <div className="font-semibold text-xs text-slate-800 line-clamp-2">
                              {bm.sulekha.service_name}
                            </div>
                            <div>{renderPriceBadge(bm.sulekha)}</div>
                            <div className="text-[11px] text-slate-500">
                              Unit: {bm.sulekha.price_unit || 'table guide'}
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs text-slate-400 italic py-2">
                            No comparable published price
                          </div>
                        )}
                      </div>
                      {bm.sulekha && (
                        <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between text-[11px]">
                          {bm.sulekha.is_locality_specific ? (
                            <span className="text-amber-700 font-medium">Locality Specific</span>
                          ) : (
                            <span className="text-emerald-700 font-medium">Citywide</span>
                          )}
                          <a
                            href={bm.sulekha.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#C8102E] hover:underline flex items-center gap-0.5"
                          >
                            Source <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* VIEW 2: Full Comparison Catalog Table & Faceted Filters */}
        {activeTab === 'catalogue' && (
          <div className="space-y-6">
            {/* Filter Bar */}
            <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-2xs space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <span className="font-bold text-sm text-slate-900 flex items-center gap-2">
                  <Tag className="w-4 h-4 text-[#C8102E]" /> Multi-Criteria Dataset Filters
                </span>
                <button
                  onClick={resetFilters}
                  className="text-xs text-slate-500 hover:text-[#C8102E] flex items-center gap-1 font-medium transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Clear All Filters
                </button>
              </div>

              {/* Search Box */}
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  placeholder="Search service task, provider, or notes (e.g. tap repair, deep clean, RO filter)..."
                  className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-300 text-xs sm:text-sm focus:outline-hidden focus:ring-2 focus:ring-[#C8102E] focus:border-transparent bg-slate-50/50"
                />
              </div>

              {/* Dropdown Filters */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 mb-1 uppercase tracking-wider">
                    Service Category
                  </label>
                  <select
                    value={category}
                    onChange={(e) => {
                      setCategory(e.target.value);
                      setPage(1);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs bg-white focus:ring-2 focus:ring-[#C8102E]"
                  >
                    {categoriesList.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 mb-1 uppercase tracking-wider">
                    Platform
                  </label>
                  <select
                    value={platform}
                    onChange={(e) => {
                      setPlatform(e.target.value);
                      setPage(1);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs bg-white focus:ring-2 focus:ring-[#C8102E]"
                  >
                    <option value="All">All Platforms (4)</option>
                    <option value="Urban Company">Urban Company (52)</option>
                    <option value="NoBroker">NoBroker (51)</option>
                    <option value="Justdial">Justdial (20)</option>
                    <option value="Sulekha">Sulekha (19)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 mb-1 uppercase tracking-wider">
                    Price Type
                  </label>
                  <select
                    value={priceType}
                    onChange={(e) => {
                      setPriceType(e.target.value);
                      setPage(1);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs bg-white focus:ring-2 focus:ring-[#C8102E]"
                  >
                    <option value="All">All Price Types</option>
                    <option value="FIXED">Fixed (56)</option>
                    <option value="STARTING_FROM">Starting From (50)</option>
                    <option value="PRICE_RANGE">Price Range (29)</option>
                    <option value="QUOTATION_REQUIRED">Quote Required (3)</option>
                    <option value="UNPUBLISHED">Unpublished (4)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 mb-1 uppercase tracking-wider">
                    Geographic Scope
                  </label>
                  <select
                    value={scopeFilter}
                    onChange={(e) => {
                      setScopeFilter(e.target.value);
                      setPage(1);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs bg-white focus:ring-2 focus:ring-[#C8102E]"
                  >
                    <option value="All">All Scopes</option>
                    <option value="citywide_only">Citywide Confirmed Only (109)</option>
                    <option value="locality_only">Locality Specific / Caveats (33)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 mb-1 uppercase tracking-wider">
                    Sort Results
                  </label>
                  <select
                    value={`${sortBy}:${sortDir}`}
                    onChange={(e) => {
                      const [b, d] = e.target.value.split(':');
                      setSortBy(b);
                      setSortDir(d);
                      setPage(1);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs bg-white focus:ring-2 focus:ring-[#C8102E]"
                  >
                    <option value="service_name:asc">Task Name (A → Z)</option>
                    <option value="price_min:asc">Lowest Listed Price (Ascending)</option>
                    <option value="price_min:desc">Highest Listed Price (Descending)</option>
                    <option value="platform:asc">Platform Name</option>
                    <option value="category:asc">Category Name</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Results Counter */}
            <div className="flex items-center justify-between text-xs text-slate-600 px-1">
              <span>
                Showing <strong>{records.length}</strong> of <strong>{totalRecords}</strong> pricing records
              </span>
              <span>
                Page <strong>{page}</strong> of <strong>{totalPages}</strong>
              </span>
            </div>

            {/* Loading State */}
            {loading && (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 space-y-3">
                <div className="w-8 h-8 border-3 border-[#C8102E] border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-xs font-semibold">Loading Bengaluru price comparison records...</p>
              </div>
            )}

            {/* Error State */}
            {!loading && error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-800 space-y-2">
                <AlertTriangle className="w-6 h-6 text-red-600 mx-auto" />
                <p className="font-bold text-sm">{error}</p>
                <button
                  onClick={resetFilters}
                  className="px-3 py-1.5 bg-[#C8102E] text-white rounded-lg text-xs font-semibold hover:bg-red-700"
                >
                  Reset Filters & Retry
                </button>
              </div>
            )}

            {/* Empty State */}
            {!loading && !error && records.length === 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 space-y-3">
                <HelpCircle className="w-8 h-8 text-slate-400 mx-auto" />
                <p className="text-sm font-bold text-slate-800">No matching price comparison records found</p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Try clearing the search query or selecting a broader category / platform filter.
                </p>
                <button
                  onClick={resetFilters}
                  className="px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800"
                >
                  Clear Filters
                </button>
              </div>
            )}

            {/* Table View */}
            {!loading && !error && records.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase tracking-wider text-[11px] font-bold">
                        <th className="py-3 px-4">Platform & Provider</th>
                        <th className="py-3 px-4">Category & Service Task</th>
                        <th className="py-3 px-4">Published Price</th>
                        <th className="py-3 px-4">Unit & Scope</th>
                        <th className="py-3 px-4">Geographic Coverage</th>
                        <th className="py-3 px-4 text-center">Status</th>
                        <th className="py-3 px-4 text-right">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {records.map((r) => {
                        const isExpanded = expandedRow === r.id;
                        return (
                          <React.Fragment key={r.id}>
                            <tr className="hover:bg-slate-50/80 transition-colors">
                              {/* Platform */}
                              <td className="py-3 px-4 align-top">
                                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${getPlatformColor(r.source_platform)}`}>
                                  {r.source_platform}
                                </span>
                                <div className="text-[11px] text-slate-500 font-medium mt-1">
                                  {r.provider_name}
                                </div>
                              </td>

                              {/* Service Name */}
                              <td className="py-3 px-4 align-top max-w-xs">
                                <div className="font-bold text-slate-900 text-xs sm:text-sm">
                                  {r.service_name}
                                </div>
                                <div className="text-[11px] text-slate-500 mt-0.5">
                                  {r.service_category}
                                </div>
                              </td>

                              {/* Price */}
                              <td className="py-3 px-4 align-top whitespace-nowrap">
                                {renderPriceBadge(r)}
                              </td>

                              {/* Unit & Scope */}
                              <td className="py-3 px-4 align-top max-w-xs">
                                <div className="text-slate-800 font-medium">
                                  {r.price_unit || 'per task'}
                                </div>
                                {r.price_scope && (
                                  <div className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                                    {r.price_scope}
                                  </div>
                                )}
                              </td>

                              {/* Geographic Scope */}
                              <td className="py-3 px-4 align-top">
                                {r.is_locality_specific ? (
                                  <div className="flex flex-col gap-0.5">
                                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                                      <AlertTriangle className="w-3 h-3 text-amber-600" /> Locality-specific / Unconfirmed
                                    </span>
                                    <span className="text-[10px] text-slate-500 truncate max-w-xs" title={r.geographic_scope}>
                                      {r.geographic_scope}
                                    </span>
                                  </div>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                                    <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Citywide Confirmed
                                  </span>
                                )}
                              </td>

                              {/* Verification Status */}
                              <td className="py-3 px-4 align-top text-center">
                                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  r.verification_status === 'SOURCE_CORROBORATED'
                                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                                }`}>
                                  {r.verification_status === 'SOURCE_CORROBORATED' ? 'Corroborated' : 'Discovered'}
                                </span>
                              </td>

                              {/* Expand Action */}
                              <td className="py-3 px-4 align-top text-right">
                                <button
                                  onClick={() => setExpandedRow(isExpanded ? null : r.id)}
                                  className="text-xs font-semibold text-slate-600 hover:text-[#C8102E] inline-flex items-center gap-1 transition-colors"
                                >
                                  {isExpanded ? 'Less' : 'Notes'}
                                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                </button>
                              </td>
                            </tr>

                            {/* Expanded Details Row */}
                            {isExpanded && (
                              <tr className="bg-slate-50/90 border-b border-slate-200">
                                <td colSpan={7} className="p-4 sm:p-5">
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                                    <div className="space-y-1">
                                      <span className="font-bold text-slate-700">Detailed Scope & Inclusions:</span>
                                      <p className="text-slate-600 bg-white p-2.5 rounded border border-slate-200 leading-relaxed">
                                        {r.price_scope || 'Standard service scope as specified on official platform listing.'}
                                      </p>
                                    </div>
                                    <div className="space-y-1">
                                      <span className="font-bold text-slate-700">Research Notes & Rate Context:</span>
                                      <p className="text-slate-600 bg-white p-2.5 rounded border border-slate-200 leading-relaxed">
                                        {r.notes || 'Rate card collected during October 2026 price audit.'}
                                      </p>
                                    </div>
                                    <div className="space-y-2">
                                      <span className="font-bold text-slate-700">Source Provenance:</span>
                                      <div className="bg-white p-2.5 rounded border border-slate-200 space-y-1.5">
                                        <div className="flex items-center justify-between text-[11px]">
                                          <span className="text-slate-500">Date Checked:</span>
                                          <span className="font-semibold text-slate-800">{r.source_checked_date}</span>
                                        </div>
                                        <div className="flex items-center justify-between text-[11px]">
                                          <span className="text-slate-500">Geographic Applicability:</span>
                                          <span className="font-semibold text-slate-800 truncate max-w-[160px]" title={r.geographic_scope}>
                                            {r.geographic_scope}
                                          </span>
                                        </div>
                                        <div className="pt-1 border-t border-slate-100">
                                          <a
                                            href={r.source_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-[#C8102E] font-bold hover:underline inline-flex items-center gap-1"
                                          >
                                            View Official Sourced Web Page <ExternalLink className="w-3.5 h-3.5" />
                                          </a>
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Footer */}
                {totalPages > 1 && (
                  <div className="bg-slate-50 border-t border-slate-200 px-4 py-3 flex items-center justify-between">
                    <button
                      onClick={() => setPage((p) => Math.max(p - 1, 1))}
                      disabled={page === 1}
                      className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed bg-white"
                    >
                      Previous
                    </button>
                    <span className="text-xs text-slate-600 font-medium">
                      Page <strong>{page}</strong> of <strong>{totalPages}</strong>
                    </span>
                    <button
                      onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                      disabled={page === totalPages}
                      className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed bg-white"
                    >
                      Next
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
