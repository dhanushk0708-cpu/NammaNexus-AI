'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import {
  Search,
  Filter,
  Star,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Building2,
  MapPin,
  CheckCircle2,
  FileText,
  X,
  Layers,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Database,
  Grid3X3,
  ListFilter,
  Info,
  Clock,
  ArrowLeft,
} from 'lucide-react';
import { Candidate } from '../page';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const BANGALORE_AREAS = [
  'All Areas',
  'Kengeri',
  'Rajarajeshwari Nagar',
  'Vijayanagar',
  'Jayanagar',
  'JP Nagar',
  'BTM Layout',
  'HSR Layout',
  'Marathahalli',
];

const SERVICE_CATEGORIES = [
  'All Categories',
  'Plumbing',
  'AC repair and servicing',
  'Electrical services',
  'House cleaning',
  'Pest control',
  'Appliance repair',
  'Water purifier/RO services',
  'Carpentry',
];

interface CoverageCell {
  id: string;
  batch_id: string;
  area: string;
  clean_area: string;
  service_category: string;
  research_status: string;
  provider_1_name?: string | null;
  provider_2_name?: string | null;
  providers_found: number;
  evidence_summary?: string | null;
  limitations?: string | null;
}

interface OverviewMetrics {
  total_candidates: number;
  distinct_businesses: number;
  total_areas: number;
  total_categories: number;
  total_coverage_cells: number;
  completed_coverage_cells: number;
  published_prices_count: number;
  ratings_count: number;
  verification_breakdown: Record<string, number>;
  price_type_breakdown: Record<string, number>;
  areas_list: string[];
  categories_list: string[];
  disclaimer: string;
}

export default function NammaServeResearchComparePage() {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [coverageCells, setCoverageCells] = useState<CoverageCell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [area, setArea] = useState('All Areas');
  const [category, setCategory] = useState('All Categories');
  const [batch, setBatch] = useState('all');
  const [verStatus, setVerStatus] = useState('all');
  const [priceType, setPriceType] = useState('all');
  const [hasPrice, setHasPrice] = useState<string>('all');
  const [hasRating, setHasRating] = useState<string>('all');

  // Sorting & Pagination
  const [sortBy, setSortBy] = useState<'rank' | 'rating' | 'price_amount' | 'name'>('rank');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Selected for Deep-Dive Modal
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [viewTab, setViewTab] = useState<'overview' | 'raw_json'>('overview');

  // Load Overview Metrics & Coverage
  useEffect(() => {
    async function fetchMetadata() {
      try {
        const [overviewRes, coverageRes] = await Promise.all([
          fetch(`${API_BASE}/nammaserve/research/overview`),
          fetch(`${API_BASE}/nammaserve/research/coverage`),
        ]);

        if (overviewRes.ok) {
          const oData = await overviewRes.json();
          setMetrics(oData);
        }
        if (coverageRes.ok) {
          const cData = await coverageRes.json();
          setCoverageCells(cData.cells || []);
        }
      } catch (err) {
        console.error('Error fetching research overview:', err);
      }
    }
    fetchMetadata();
  }, []);

  // Load Candidates
  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (area !== 'All Areas') params.append('area', area);
        if (category !== 'All Categories') params.append('category', category);
        if (batch !== 'all') params.append('batch', batch);
        if (verStatus !== 'all') params.append('verification_status', verStatus);
        if (priceType !== 'all') params.append('price_type', priceType);
        if (hasPrice === 'yes') params.append('has_price', 'true');
        if (hasPrice === 'no') params.append('has_price', 'false');
        if (hasRating === 'yes') params.append('has_rating', 'true');
        if (hasRating === 'no') params.append('has_rating', 'false');
        if (search.trim()) params.append('search', search.trim());

        params.append('sort_by', sortBy);
        params.append('sort_dir', sortDir);
        params.append('limit', '128'); // Fetch all matching candidates for client table pagination

        const res = await fetch(`${API_BASE}/nammaserve/research/candidates?${params.toString()}`, {
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!ignore) {
          setCandidates(data.items || []);
          setPage(1);
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        console.error('Failed to load comparison candidates:', err);
        if (!ignore) {
          setError('Failed to load research candidates from backend.');
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
  }, [area, category, batch, verStatus, priceType, hasPrice, hasRating, search, sortBy, sortDir]);

  // Paginated records
  const paginatedCandidates = useMemo(() => {
    const start = (page - 1) * pageSize;
    return candidates.slice(start, start + pageSize);
  }, [candidates, page, pageSize]);

  const totalPages = Math.ceil(candidates.length / pageSize) || 1;

  const handleSort = (field: 'rank' | 'rating' | 'price_amount' | 'name') => {
    if (sortBy === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDir('asc');
    }
  };

  const handleClearFilters = () => {
    setSearch('');
    setArea('All Areas');
    setCategory('All Categories');
    setBatch('all');
    setVerStatus('all');
    setPriceType('all');
    setHasPrice('all');
    setHasRating('all');
    setSortBy('rank');
    setSortDir('asc');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/nammaserve"
              className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
              title="Return to Marketplace"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-slate-900 text-base tracking-tight">NammaServe Research</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                  Gemini Evaluator
                </span>
              </div>
              <p className="text-[11px] text-slate-500">128 Local Home-Service Provider Comparison Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/nammaserve"
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Switch to Marketplace View
            </Link>
          </div>
        </div>
      </header>

      {/* Prominent Research Notice Banner */}
      <div className="bg-amber-50 border-b border-amber-200 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-start gap-3 text-xs text-amber-900">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>Research Data Notice:</strong> The records below represent provider and pricing claims extracted
            from public directory listings, platform landing pages, and Google Maps profiles during Gemini research.
            Information may not be independently verified. Prices, availability, service coverage, and provider
            identities should be confirmed directly before booking.
          </p>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6 flex-1 w-full">
        {/* KPI Metrics Cards */}
        {metrics && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Total Records</span>
              <div className="text-2xl font-black text-slate-900 mt-1">{metrics.total_candidates}</div>
              <span className="text-[10px] text-slate-500">4 batches evaluated</span>
            </div>
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Distinct Businesses</span>
              <div className="text-2xl font-black text-slate-900 mt-1">{metrics.distinct_businesses}</div>
              <span className="text-[10px] text-slate-500">Deduplicated entities</span>
            </div>
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Researched Areas</span>
              <div className="text-2xl font-black text-slate-900 mt-1">{metrics.total_areas}</div>
              <span className="text-[10px] text-slate-500">Bengaluru zones</span>
            </div>
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Service Verticals</span>
              <div className="text-2xl font-black text-slate-900 mt-1">{metrics.total_categories}</div>
              <span className="text-[10px] text-slate-500">Core home categories</span>
            </div>
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Published Prices</span>
              <div className="text-2xl font-black text-slate-900 mt-1">{metrics.published_prices_count}</div>
              <span className="text-[10px] text-slate-500">Fixed or starting rates</span>
            </div>
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Coverage Matrix</span>
              <div className="text-2xl font-black text-emerald-600 mt-1">
                {metrics.completed_coverage_cells}/{metrics.total_coverage_cells}
              </div>
              <span className="text-[10px] text-slate-500">100% Completed</span>
            </div>
          </div>
        )}

        {/* Research Coverage Heatmap / Matrix Accordion */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-2xs">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Grid3X3 className="w-4 h-4 text-purple-600" />
              <h3 className="text-sm font-bold text-slate-900">Area × Category Research Matrix (64 Combinations)</h3>
            </div>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              64 of 64 Completed with Results
            </span>
          </div>

          <div className="p-4 overflow-x-auto">
            <p className="text-xs text-slate-500 mb-3">
              Click any cell to filter the comparison table to that specific area and category pair:
            </p>
            <div className="min-w-[800px] border border-slate-200 rounded-xl overflow-hidden text-xs">
              <div className="grid grid-cols-9 bg-slate-100 font-bold text-slate-700 p-2.5 border-b border-slate-200">
                <div>Area \ Category</div>
                {SERVICE_CATEGORIES.slice(1).map((c) => (
                  <div key={c} className="truncate text-center" title={c}>
                    {c.split(' ')[0]}
                  </div>
                ))}
              </div>
              {BANGALORE_AREAS.slice(1).map((a) => (
                <div key={a} className="grid grid-cols-9 border-b border-slate-100 last:border-none p-2 items-center hover:bg-slate-50">
                  <div className="font-semibold text-slate-800 truncate pr-2" title={a}>
                    {a}
                  </div>
                  {SERVICE_CATEGORIES.slice(1).map((c) => {
                    const active = area === a && category === c;
                    return (
                      <button
                        key={`${a}-${c}`}
                        onClick={() => {
                          setArea(a);
                          setCategory(c);
                        }}
                        className={`mx-1 py-1 px-1.5 rounded text-[11px] font-bold text-center transition-all ${
                          active
                            ? 'bg-purple-600 text-white shadow-xs scale-105'
                            : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200/80'
                        }`}
                        title={`${a} • ${c} (2 providers found)`}
                      >
                        2 Prov
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Filters Bar */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search provider name, specific service, or address..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
              />
            </div>
            <button
              onClick={handleClearFilters}
              className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 shrink-0"
            >
              Clear All Filters
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
            {/* Area */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">Area</label>
              <select
                value={area}
                onChange={(e) => setArea(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium"
              >
                {BANGALORE_AREAS.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>

            {/* Category */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium truncate"
              >
                {SERVICE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Batch */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">Batch</label>
              <select
                value={batch}
                onChange={(e) => setBatch(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium"
              >
                <option value="all">All Batches (1-4)</option>
                <option value="batch1">Batch 1 (Kengeri & RR Nagar)</option>
                <option value="batch2">Batch 2 (Vijayanagar & Jayanagar)</option>
                <option value="batch3">Batch 3 (JP Nagar & BTM Layout)</option>
                <option value="batch4">Batch 4 (HSR & Marathahalli)</option>
              </select>
            </div>

            {/* Verification */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">Verification</label>
              <select
                value={verStatus}
                onChange={(e) => setVerStatus(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium"
              >
                <option value="all">All Verification</option>
                <option value="SOURCE_CORROBORATED">Source Corroborated</option>
                <option value="DISCOVERED">Discovered</option>
              </select>
            </div>

            {/* Price Available */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">Price Published</label>
              <select
                value={hasPrice}
                onChange={(e) => setHasPrice(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium"
              >
                <option value="all">Any Price Status</option>
                <option value="yes">Has Published Price</option>
                <option value="no">Price Not Published</option>
              </select>
            </div>

            {/* Rating Available */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 mb-1">Google Rating</label>
              <select
                value={hasRating}
                onChange={(e) => setHasRating(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium"
              >
                <option value="all">Any Rating Status</option>
                <option value="yes">Has Published Rating</option>
                <option value="no">Unrated</option>
              </select>
            </div>
          </div>
        </div>

        {/* Comparison Table */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between text-xs">
            <span className="font-bold text-slate-800">
              Matching Records: <strong>{candidates.length}</strong> providers
            </span>
            <div className="text-slate-500">
              Page {page} of {totalPages}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                  <th
                    className="p-3 cursor-pointer hover:bg-slate-100"
                    onClick={() => handleSort('rank')}
                  >
                    <div className="flex items-center gap-1">
                      Rank <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th
                    className="p-3 cursor-pointer hover:bg-slate-100"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center gap-1">
                      Provider Name <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Area</th>
                  <th
                    className="p-3 cursor-pointer hover:bg-slate-100"
                    onClick={() => handleSort('rating')}
                  >
                    <div className="flex items-center gap-1">
                      Rating <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th
                    className="p-3 cursor-pointer hover:bg-slate-100"
                    onClick={() => handleSort('price_amount')}
                  >
                    <div className="flex items-center gap-1">
                      Published Price <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="p-3">Verification</th>
                  <th className="p-3">Evidence Source</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="p-12 text-center text-slate-400">
                      Loading comparison records...
                    </td>
                  </tr>
                ) : paginatedCandidates.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="p-12 text-center text-slate-500">
                      No research providers match the specified filters.
                    </td>
                  </tr>
                ) : (
                  paginatedCandidates.map((cand) => (
                    <tr key={cand.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="p-3 font-mono text-slate-500">{cand.provider_rank}</td>
                      <td className="p-3 font-bold text-slate-900 max-w-[200px] truncate" title={cand.provider_name}>
                        {cand.provider_name}
                      </td>
                      <td className="p-3 text-slate-700">{cand.service_category}</td>
                      <td className="p-3 text-slate-700">{cand.area_name}</td>
                      <td className="p-3 font-semibold">
                        {cand.rating ? (
                          <span className="flex items-center gap-1 text-amber-700 bg-amber-50 px-2 py-0.5 rounded w-fit">
                            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                            {cand.rating.toFixed(1)}{' '}
                            <span className="text-slate-400 font-normal">({cand.review_count || 0})</span>
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">—</span>
                        )}
                      </td>
                      <td className="p-3">
                        {cand.price_amount !== null && cand.price_amount !== undefined ? (
                          <span className="font-bold text-slate-900">
                            ₹{cand.price_amount.toLocaleString('en-IN')}{' '}
                            <span className="text-[10px] text-slate-500 font-normal">
                              {cand.price_type === 'STARTING_AT' ? '(Starts at)' : '(Fixed)'}
                            </span>
                          </span>
                        ) : cand.price_type === 'QUOTATION_REQUIRED' ? (
                          <span className="text-slate-600 font-medium">Quote Required</span>
                        ) : (
                          <span className="text-slate-400 italic">—</span>
                        )}
                      </td>
                      <td className="p-3">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${
                            cand.verification_status === 'SOURCE_CORROBORATED'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : 'bg-amber-50 text-amber-800 border border-amber-200'
                          }`}
                        >
                          <ShieldCheck className="w-3 h-3" />
                          {cand.verification_status === 'SOURCE_CORROBORATED'
                            ? 'Corroborated'
                            : 'Discovered'}
                        </span>
                      </td>
                      <td className="p-3 max-w-[140px] truncate">
                        {cand.primary_source_url ? (
                          <a
                            href={cand.primary_source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[#C8102E] hover:underline inline-flex items-center gap-1 truncate"
                            title={cand.primary_source_url}
                          >
                            <ExternalLink className="w-3 h-3 shrink-0" />
                            <span className="truncate">View Link</span>
                          </a>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => {
                            setSelectedCandidate(cand);
                            setViewTab('overview');
                          }}
                          className="font-bold text-xs text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 px-2.5 py-1 rounded-lg transition-colors"
                        >
                          Inspect Evidence
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500">
                Showing {Math.min((page - 1) * pageSize + 1, candidates.length)} to{' '}
                {Math.min(page * pageSize, candidates.length)} of {candidates.length} records
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  className="px-2.5 py-1 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-2 font-bold text-slate-700">
                  {page} / {totalPages}
                </span>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                  className="px-2.5 py-1 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Deep-Dive Evidence Inspection Modal */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    {selectedCandidate.service_category}
                  </span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                    Batch: {selectedCandidate.batch_id} • Rank {selectedCandidate.provider_rank}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-slate-900">{selectedCandidate.provider_name}</h3>
                <p className="text-xs text-slate-500">{selectedCandidate.requested_area}</p>
              </div>
              <button
                onClick={() => setSelectedCandidate(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex gap-2 border-b border-slate-100 pb-2 text-xs font-semibold">
              <button
                onClick={() => setViewTab('overview')}
                className={`px-3 py-1.5 rounded-lg transition-colors ${
                  viewTab === 'overview' ? 'bg-purple-600 text-white' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                Evidence & Sentiments
              </button>
              <button
                onClick={() => setViewTab('raw_json')}
                className={`px-3 py-1.5 rounded-lg transition-colors ${
                  viewTab === 'raw_json' ? 'bg-purple-600 text-white' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                Raw CSV Row (JSON)
              </button>
            </div>

            {viewTab === 'overview' ? (
              <div className="space-y-3 text-xs">
                {/* Evidence Summary */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                  <span className="font-bold text-slate-700">Evidence Summary:</span>
                  <p className="text-slate-700 leading-relaxed">{selectedCandidate.evidence_summary}</p>
                </div>

                {/* Pricing & Ratings Breakdown */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                    <span className="font-bold text-slate-700">Pricing Data:</span>
                    <p className="text-slate-800">
                      <strong>Type:</strong> {selectedCandidate.price_type || 'None'}
                    </p>
                    {selectedCandidate.price_amount !== null && (
                      <p className="text-slate-800 font-extrabold text-sm text-[#C8102E]">
                        ₹{selectedCandidate.price_amount} {selectedCandidate.price_unit}
                      </p>
                    )}
                    {selectedCandidate.price_scope && (
                      <p className="text-slate-600 text-[11px]">{selectedCandidate.price_scope}</p>
                    )}
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                    <span className="font-bold text-slate-700">Rating Profile:</span>
                    <p className="text-slate-800">
                      <strong>Score:</strong> {selectedCandidate.rating ? `${selectedCandidate.rating} / 5.0` : 'None'}
                    </p>
                    <p className="text-slate-800">
                      <strong>Review Count:</strong> {selectedCandidate.review_count || 'None'}
                    </p>
                    <p className="text-slate-800">
                      <strong>Platform:</strong> {selectedCandidate.rating_platform || 'None'}
                    </p>
                  </div>
                </div>

                {/* Review Sentiments from Batches 2-4 */}
                {selectedCandidate.review_summary && (
                  <div className="p-3 bg-purple-50/50 rounded-xl border border-purple-100 space-y-1">
                    <span className="font-bold text-purple-900">Review Sentiment Summary:</span>
                    <p className="text-slate-800 leading-relaxed">{selectedCandidate.review_summary}</p>
                  </div>
                )}

                {selectedCandidate.review_positive_themes && (
                  <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100 space-y-1">
                    <span className="font-bold text-emerald-900">Customer Praises:</span>
                    <p className="text-emerald-800">{selectedCandidate.review_positive_themes}</p>
                  </div>
                )}

                {selectedCandidate.review_summary_limitations && (
                  <div className="p-3 bg-slate-100 rounded-xl space-y-1 text-slate-600 italic">
                    <span className="font-bold text-slate-700 not-italic">Evaluation Limitations:</span>
                    <p>{selectedCandidate.review_summary_limitations}</p>
                  </div>
                )}

                {/* Source URLs */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                  <span className="font-bold text-slate-700">Corroborated Sources:</span>
                  <div className="flex flex-col gap-1 mt-1">
                    {selectedCandidate.primary_source_url && (
                      <a
                        href={selectedCandidate.primary_source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[#C8102E] hover:underline flex items-center gap-1 truncate"
                      >
                        <ExternalLink className="w-3 h-3 shrink-0" />
                        <span className="truncate">Primary: {selectedCandidate.primary_source_url}</span>
                      </a>
                    )}
                    {selectedCandidate.secondary_source_url && (
                      <a
                        href={selectedCandidate.secondary_source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[#C8102E] hover:underline flex items-center gap-1 truncate"
                      >
                        <ExternalLink className="w-3 h-3 shrink-0" />
                        <span className="truncate">Secondary: {selectedCandidate.secondary_source_url}</span>
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <pre className="p-3 bg-slate-900 text-slate-100 rounded-xl text-[11px] overflow-x-auto max-h-[350px]">
                {JSON.stringify(selectedCandidate.raw_record || selectedCandidate, null, 2)}
              </pre>
            )}

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedCandidate(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
