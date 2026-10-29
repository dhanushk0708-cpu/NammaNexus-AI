'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import {
  Search,
  MapPin,
  Star,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Phone,
  Mail,
  Globe,
  Calendar,
  Clock,
  Wrench,
  Sparkles,
  ShieldCheck,
  Building2,
  ChevronRight,
  Filter,
  X,
  Send,
  Layers,
  ArrowRight,
} from 'lucide-react';

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
  { id: 'all', name: 'All Categories', icon: '⚡' },
  { id: 'Plumbing', name: 'Plumbing', icon: '🔧' },
  { id: 'AC repair and servicing', name: 'AC Repair', icon: '❄️' },
  { id: 'Electrical services', name: 'Electrical', icon: '💡' },
  { id: 'House cleaning', name: 'House Cleaning', icon: '🧹' },
  { id: 'Pest control', name: 'Pest Control', icon: '🐜' },
  { id: 'Appliance repair', name: 'Appliance Repair', icon: '🧺' },
  { id: 'Water purifier/RO services', name: 'Water Purifier / RO', icon: '💧' },
  { id: 'Carpentry', name: 'Carpentry', icon: '🪚' },
];

export interface Candidate {
  id: string;
  batch_id: string;
  provider_id: string;
  provider_name: string;
  service_category: string;
  raw_service_category: string;
  specific_services?: string | null;
  requested_area: string;
  area_name: string;
  business_address?: string | null;
  public_phone?: string | null;
  public_email?: string | null;
  website_url?: string | null;
  contact_or_booking_url?: string | null;
  advertised_service_areas?: string | null;
  area_coverage_evidence_url?: string | null;
  price_type?: string | null;
  price_amount?: number | null;
  price_currency: string;
  price_unit?: string | null;
  price_scope?: string | null;
  price_source_url?: string | null;
  rating?: number | null;
  review_count?: number | null;
  rating_platform?: string | null;
  rating_source_url?: string | null;
  booking_method?: string | null;
  availability_status: string;
  verification_status: string;
  primary_source_url?: string | null;
  secondary_source_url?: string | null;
  research_date?: string | null;
  confidence: string;
  evidence_summary?: string | null;
  missing_information?: string | null;
  duplicate_group_id?: string | null;
  provider_rank: number;
  notes?: string | null;
  review_summary?: string | null;
  review_positive_themes?: string | null;
  review_negative_themes?: string | null;
  review_date_range?: string | null;
  review_summary_source_url?: string | null;
  review_summary_limitations?: string | null;
  raw_record?: Record<string, any>;
}

export default function NammaServeMarketplacePage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArea, setSelectedArea] = useState('All Areas');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [priceFilter, setPriceFilter] = useState<'all' | 'published_only'>('all');
  const [ratingFilter, setRatingFilter] = useState<'all' | 'rated_only'>('all');
  const [verificationFilter, setVerificationFilter] = useState<'all' | 'SOURCE_CORROBORATED' | 'DISCOVERED'>('all');

  // Modals
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [bookingCandidate, setBookingCandidate] = useState<Candidate | null>(null);
  const [bookingForm, setBookingForm] = useState({
    customer_name: '',
    customer_phone: '',
    customer_email: '',
    customer_address: '',
    preferred_date: '',
    preferred_time_slot: 'Morning (9 AM - 12 PM)',
    issue_description: '',
  });
  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [bookingSuccess, setBookingSuccess] = useState<{ id: string; message: string } | null>(null);
  const [bookingError, setBookingError] = useState<string | null>(null);

  // Fetch candidates
  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (selectedArea !== 'All Areas') params.append('area', selectedArea);
        if (selectedCategory !== 'all') params.append('category', selectedCategory);
        if (priceFilter === 'published_only') params.append('has_price', 'true');
        if (ratingFilter === 'rated_only') params.append('has_rating', 'true');
        if (verificationFilter !== 'all') params.append('verification_status', verificationFilter);
        if (searchQuery.trim()) params.append('search', searchQuery.trim());
        params.append('limit', '100');

        const res = await fetch(`${API_BASE}/nammaserve/research/candidates?${params.toString()}`, {
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!ignore) {
          setCandidates(data.items || []);
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        console.error('Failed to fetch research candidates:', err);
        if (!ignore) {
          setError('Unable to load live provider data from backend.');
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }, searchQuery.trim() ? 300 : 0);

    return () => {
      ignore = true;
      controller.abort();
      clearTimeout(timer);
    };
  }, [selectedArea, selectedCategory, priceFilter, ratingFilter, verificationFilter, searchQuery]);

  const handleBookingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bookingCandidate) return;
    setBookingSubmitting(true);
    setBookingError(null);
    setBookingSuccess(null);

    try {
      const payload = {
        candidate_id: bookingCandidate.id,
        provider_name: bookingCandidate.provider_name,
        service_category: bookingCandidate.service_category,
        area: bookingCandidate.area_name,
        customer_name: bookingForm.customer_name,
        customer_phone: bookingForm.customer_phone,
        customer_email: bookingForm.customer_email || undefined,
        customer_address: bookingForm.customer_address || undefined,
        preferred_date: bookingForm.preferred_date || undefined,
        preferred_time_slot: bookingForm.preferred_time_slot || undefined,
        issue_description: bookingForm.issue_description,
      };

      const res = await fetch(`${API_BASE}/nammaserve/booking-requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to submit booking request');
      }

      const resData = await res.json();
      setBookingSuccess({
        id: resData.id,
        message: resData.confirmation_message || 'Booking request submitted successfully!',
      });
      setBookingForm({
        customer_name: '',
        customer_phone: '',
        customer_email: '',
        customer_address: '',
        preferred_date: '',
        preferred_time_slot: 'Morning (9 AM - 12 PM)',
        issue_description: '',
      });
    } catch (err: any) {
      setBookingError(err.message || 'Error submitting booking');
    } finally {
      setBookingSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      {/* Top Banner Notice */}
      <div className="bg-amber-50 border-b border-amber-200/80 px-4 py-2 text-xs text-amber-900 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 font-medium">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            Research-backed local home services in Bengaluru. Providers require direct confirmation before booking.
          </span>
        </div>
        <Link
          href="/nammaserve/research-compare"
          className="font-bold text-[#C8102E] hover:underline flex items-center gap-1 shrink-0"
        >
          Research & Comparison Dashboard <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200 pt-10 pb-12 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 border border-red-200 text-[#C8102E] text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            NammaServe Civic Marketplace
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight">
            Trusted Local Services, <span className="text-[#C8102E]">Made Simple.</span>
          </h1>
          <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Discover verified independent technicians, specialized workshops, and platform rate cards across Bengaluru.
            Transparent ratings, documented local evidence, and honest pricing.
          </p>

          {/* Search Box */}
          <div className="mt-6 max-w-3xl mx-auto bg-white p-2 rounded-2xl shadow-sm border border-slate-200 flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1 flex items-center">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5" />
              <input
                type="text"
                placeholder="Search plumber, electrician, AC repair, or company name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20 text-slate-800"
              />
            </div>
            <div className="relative sm:w-60 flex items-center">
              <MapPin className="w-4 h-4 text-[#C8102E] absolute left-3.5 pointer-events-none" />
              <select
                value={selectedArea}
                onChange={(e) => setSelectedArea(e.target.value)}
                className="w-full pl-10 pr-8 py-2.5 text-sm rounded-xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20 text-slate-800 font-medium cursor-pointer"
              >
                {BANGALORE_AREAS.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={() => {}}
              className="bg-[#C8102E] hover:bg-[#A50D25] text-white px-6 py-2.5 rounded-xl font-semibold text-sm transition-colors shadow-sm shrink-0"
            >
              Search
            </button>
          </div>
        </div>
      </section>

      {/* Service Categories Carousel / Grid */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-8 w-full">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Popular Service Verticals</h2>
            <p className="text-xs text-slate-500">Select a category to view local providers</p>
          </div>
          {selectedCategory !== 'all' && (
            <button
              onClick={() => setSelectedCategory('all')}
              className="text-xs font-semibold text-[#C8102E] hover:underline"
            >
              Clear Category Filter
            </button>
          )}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-2.5">
          {SERVICE_CATEGORIES.map((cat) => {
            const active = selectedCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all ${
                  active
                    ? 'bg-red-50 border-red-300 text-[#C8102E] shadow-xs scale-102 font-bold'
                    : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700'
                }`}
              >
                <span className="text-2xl mb-1">{cat.icon}</span>
                <span className="text-xs leading-tight line-clamp-2">{cat.name}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Main Content & Providers List */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-16 flex-1 w-full">
        {/* Filter controls row */}
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 mb-6 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-500 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Filters:
            </span>

            {/* Price filter */}
            <select
              value={priceFilter}
              onChange={(e) => setPriceFilter(e.target.value as any)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 font-medium"
            >
              <option value="all">All Pricing Types</option>
              <option value="published_only">Published Rates Only</option>
            </select>

            {/* Rating filter */}
            <select
              value={ratingFilter}
              onChange={(e) => setRatingFilter(e.target.value as any)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 font-medium"
            >
              <option value="all">All Ratings</option>
              <option value="rated_only">Google Maps Rated Only</option>
            </select>

            {/* Verification filter */}
            <select
              value={verificationFilter}
              onChange={(e) => setVerificationFilter(e.target.value as any)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 font-medium"
            >
              <option value="all">All Statuses</option>
              <option value="SOURCE_CORROBORATED">Source Corroborated</option>
              <option value="DISCOVERED">Discovered</option>
            </select>
          </div>

          <div className="text-slate-500 font-medium">
            Showing <strong className="text-slate-900">{candidates.length}</strong> provider records
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && (
          <div className="py-20 text-center text-slate-500 space-y-2">
            <div className="w-8 h-8 border-2 border-[#C8102E] border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm">Loading local service providers...</p>
          </div>
        )}

        {error && !loading && (
          <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-center text-red-700 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && candidates.length === 0 && (
          <div className="p-12 bg-white border border-slate-200 rounded-2xl text-center space-y-3">
            <Building2 className="w-10 h-10 text-slate-300 mx-auto" />
            <h3 className="text-base font-bold text-slate-800">No Providers Match Your Query</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              We did not find any researched providers in <strong>{selectedArea}</strong> for{' '}
              <strong>{selectedCategory !== 'all' ? selectedCategory : 'selected filters'}</strong>. Try clearing filters or exploring neighbouring localities.
            </p>
            <button
              onClick={() => {
                setSelectedArea('All Areas');
                setSelectedCategory('all');
                setSearchQuery('');
                setPriceFilter('all');
                setRatingFilter('all');
              }}
              className="mt-2 text-xs font-bold text-[#C8102E] border border-red-200 bg-red-50 px-4 py-2 rounded-lg hover:bg-red-100"
            >
              Reset All Filters
            </button>
          </div>
        )}

        {/* Providers Cards Grid */}
        {!loading && !error && candidates.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {candidates.map((cand) => (
              <div
                key={cand.id}
                className="bg-white rounded-2xl border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all p-5 flex flex-col justify-between"
              >
                <div>
                  {/* Top Header: Category & Verification */}
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <span className="text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md truncate">
                      {cand.service_category}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                        cand.verification_status === 'SOURCE_CORROBORATED'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}
                    >
                      <ShieldCheck className="w-3 h-3" />
                      {cand.verification_status === 'SOURCE_CORROBORATED'
                        ? 'Corroborated'
                        : 'Discovered'}
                    </span>
                  </div>

                  {/* Provider Name */}
                  <h3 className="text-base font-bold text-slate-900 line-clamp-1 hover:text-[#C8102E] transition-colors">
                    {cand.provider_name}
                  </h3>

                  {/* Area */}
                  <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                    <MapPin className="w-3 h-3 text-[#C8102E] shrink-0" />
                    <span className="truncate">{cand.area_name || cand.requested_area}</span>
                  </p>

                  {/* Rating & Review */}
                  <div className="flex items-center gap-2 mt-2.5 text-xs">
                    {cand.rating ? (
                      <div className="flex items-center gap-1 font-bold text-slate-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200/60">
                        <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                        <span>{cand.rating.toFixed(1)}</span>
                        {cand.review_count && (
                          <span className="text-slate-400 font-normal">({cand.review_count})</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-slate-400 italic text-[11px]">Rating not published</span>
                    )}

                    {cand.rating_platform && (
                      <span className="text-[11px] text-slate-500 font-medium truncate">
                        via {cand.rating_platform}
                      </span>
                    )}
                  </div>

                  {/* Price Section */}
                  <div className="mt-3.5 p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">
                      Pricing Status
                    </div>
                    {cand.price_amount !== null && cand.price_amount !== undefined ? (
                      <div className="text-sm font-extrabold text-slate-900 mt-0.5">
                        {cand.price_type === 'STARTING_AT' ? 'Starts at ' : 'Fixed '}
                        <span className="text-[#C8102E]">₹{cand.price_amount.toLocaleString('en-IN')}</span>{' '}
                        <span className="text-xs font-normal text-slate-500">
                          {cand.price_unit ? `(${cand.price_unit})` : ''}
                        </span>
                      </div>
                    ) : cand.price_type === 'QUOTATION_REQUIRED' ? (
                      <div className="text-xs font-bold text-slate-700 mt-0.5">
                        Quotation Required on Inspection
                      </div>
                    ) : (
                      <div className="text-xs text-slate-500 italic mt-0.5">
                        Price upon direct inquiry
                      </div>
                    )}
                  </div>

                  {/* Evidence snippet */}
                  {cand.evidence_summary && (
                    <p className="text-[11px] text-slate-500 mt-3 line-clamp-2 leading-relaxed">
                      {cand.evidence_summary}
                    </p>
                  )}
                </div>

                {/* Card Actions */}
                <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                  <button
                    onClick={() => setSelectedCandidate(cand)}
                    className="text-xs font-bold text-slate-700 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    View Details
                  </button>
                  <button
                    onClick={() => {
                      setBookingCandidate(cand);
                      setBookingSuccess(null);
                      setBookingError(null);
                    }}
                    className="text-xs font-bold text-white bg-[#C8102E] hover:bg-[#A50D25] px-3.5 py-1.5 rounded-lg transition-colors shadow-2xs"
                  >
                    Request Booking
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* How It Works Section */}
      <section className="bg-white border-t border-slate-200 py-12 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto text-center space-y-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">How NammaServe Works</h2>
            <p className="text-xs text-slate-500 mt-1">Honest, transparent civic home-services discovery</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="w-8 h-8 rounded-xl bg-red-100 text-[#C8102E] font-bold flex items-center justify-center text-sm">
                1
              </div>
              <h3 className="text-sm font-bold text-slate-900">Search Your Locality</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Filter across 8 researched Bengaluru areas and 8 core categories. No fake listings or auto-generated addresses.
              </p>
            </div>
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-700 font-bold flex items-center justify-center text-sm">
                2
              </div>
              <h3 className="text-sm font-bold text-slate-900">Inspect Evidence & Sources</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Review corroborated ratings, documented rate cards, Google Maps sources, and review limitations before deciding.
              </p>
            </div>
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center text-sm">
                3
              </div>
              <h3 className="text-sm font-bold text-slate-900">Request Safe Bookings</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Submit an upfront booking request without immediate payment or fake acceptance claims. Provider confirmation required.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Provider Detail Modal */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-5">
            {/* Header */}
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                    {selectedCandidate.service_category}
                  </span>
                  <span
                    className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                      selectedCandidate.verification_status === 'SOURCE_CORROBORATED'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}
                  >
                    {selectedCandidate.verification_status === 'SOURCE_CORROBORATED'
                      ? 'Source Corroborated'
                      : 'Discovered'}
                  </span>
                </div>
                <h2 className="text-xl font-extrabold text-slate-900">{selectedCandidate.provider_name}</h2>
                <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                  <MapPin className="w-3.5 h-3.5 text-[#C8102E]" />
                  {selectedCandidate.requested_area}
                </p>
              </div>
              <button
                onClick={() => setSelectedCandidate(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Address & Public Contact Info */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {selectedCandidate.business_address && (
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                  <span className="font-semibold text-slate-500">Business Address</span>
                  <p className="text-slate-800 leading-relaxed">{selectedCandidate.business_address}</p>
                </div>
              )}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
                <span className="font-semibold text-slate-500">Public Contacts</span>
                {selectedCandidate.public_phone ? (
                  <p className="text-slate-800 flex items-center gap-1.5 font-bold">
                    <Phone className="w-3.5 h-3.5 text-slate-400" /> {selectedCandidate.public_phone}
                  </p>
                ) : (
                  <p className="text-slate-400 italic">No phone published</p>
                )}
                {selectedCandidate.public_email && (
                  <p className="text-slate-800 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-slate-400" /> {selectedCandidate.public_email}
                  </p>
                )}
                {selectedCandidate.website_url && (
                  <a
                    href={selectedCandidate.website_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[#C8102E] hover:underline flex items-center gap-1 font-medium"
                  >
                    <Globe className="w-3.5 h-3.5" /> Visit Website
                  </a>
                )}
              </div>
            </div>

            {/* Services scope */}
            {selectedCandidate.specific_services && (
              <div className="space-y-1 text-xs">
                <h4 className="font-bold text-slate-900">Specific Services Offered</h4>
                <p className="text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-100 leading-relaxed">
                  {selectedCandidate.specific_services}
                </p>
              </div>
            )}

            {/* Rate & Pricing Info */}
            <div className="p-4 bg-red-50/50 rounded-2xl border border-red-100 space-y-2 text-xs">
              <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
                <span>Published Pricing Information</span>
              </h4>
              {selectedCandidate.price_amount !== null && selectedCandidate.price_amount !== undefined ? (
                <div className="text-base font-extrabold text-slate-900">
                  {selectedCandidate.price_type === 'STARTING_AT' ? 'Starting Rate: ' : 'Fixed Price: '}
                  <span className="text-[#C8102E]">₹{selectedCandidate.price_amount.toLocaleString('en-IN')}</span>{' '}
                  <span className="text-xs text-slate-600 font-normal">
                    {selectedCandidate.price_unit ? `(${selectedCandidate.price_unit})` : ''}
                  </span>
                </div>
              ) : (
                <p className="text-slate-700 italic">
                  {selectedCandidate.price_type === 'QUOTATION_REQUIRED'
                    ? 'Quotation required based on specific inspection.'
                    : 'Rates are not published online. Contact provider directly.'}
                </p>
              )}
              {selectedCandidate.price_scope && (
                <p className="text-slate-600 mt-1">
                  <strong>Scope:</strong> {selectedCandidate.price_scope}
                </p>
              )}
              {selectedCandidate.price_source_url && (
                <a
                  href={selectedCandidate.price_source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[#C8102E] hover:underline inline-flex items-center gap-1 text-[11px] font-semibold mt-1"
                >
                  <ExternalLink className="w-3 h-3" /> View Verified Price Source
                </a>
              )}
            </div>

            {/* Ratings & Reviews */}
            {selectedCandidate.rating && (
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-slate-900">Rating & Sentiment Analysis</h4>
                  <div className="flex items-center gap-1 font-bold text-slate-900 bg-amber-100 px-2 py-0.5 rounded">
                    <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                    <span>{selectedCandidate.rating.toFixed(1)}</span>
                    {selectedCandidate.review_count && <span>({selectedCandidate.review_count} reviews)</span>}
                  </div>
                </div>
                {selectedCandidate.review_positive_themes && (
                  <p className="text-emerald-800 bg-emerald-50 p-2.5 rounded-lg border border-emerald-100">
                    <strong>Customer Praises:</strong> {selectedCandidate.review_positive_themes}
                  </p>
                )}
                {selectedCandidate.review_summary_limitations && (
                  <p className="text-slate-500 text-[11px] italic">
                    <strong>Review Limitations:</strong> {selectedCandidate.review_summary_limitations}
                  </p>
                )}
                {selectedCandidate.rating_source_url && (
                  <a
                    href={selectedCandidate.rating_source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[#C8102E] hover:underline inline-flex items-center gap-1 text-[11px] font-semibold"
                  >
                    <ExternalLink className="w-3 h-3" /> View Source Reviews
                  </a>
                )}
              </div>
            )}

            {/* Evidence & Missing Info */}
            <div className="space-y-2 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="font-semibold text-slate-500">Research Evidence Summary:</span>
                <p className="text-slate-700 mt-0.5 leading-relaxed">{selectedCandidate.evidence_summary}</p>
              </div>
              {selectedCandidate.missing_information && (
                <div className="p-3 bg-amber-50/60 rounded-xl border border-amber-200/60 text-amber-900">
                  <span className="font-semibold">Missing / Unverified Details:</span>{' '}
                  {selectedCandidate.missing_information}
                </div>
              )}
            </div>

            {/* Disclaimer & CTA */}
            <div className="pt-3 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
              <span className="text-[11px] text-slate-400 italic">
                Research candidate • Subject to direct provider confirmation
              </span>
              <button
                onClick={() => {
                  setBookingCandidate(selectedCandidate);
                  setSelectedCandidate(null);
                  setBookingSuccess(null);
                  setBookingError(null);
                }}
                className="w-full sm:w-auto bg-[#C8102E] hover:bg-[#A50D25] text-white px-5 py-2.5 rounded-xl font-bold text-xs transition-colors shadow-sm"
              >
                Request a Booking
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Booking Request Modal */}
      {bookingCandidate && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-xs font-semibold text-[#C8102E] uppercase tracking-wider">
                  Request a Booking
                </span>
                <h3 className="text-lg font-bold text-slate-900">{bookingCandidate.provider_name}</h3>
                <p className="text-xs text-slate-500">
                  {bookingCandidate.service_category} • {bookingCandidate.area_name}
                </p>
              </div>
              <button
                onClick={() => setBookingCandidate(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {bookingSuccess ? (
              <div className="p-6 text-center space-y-3 bg-emerald-50 rounded-2xl border border-emerald-200">
                <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
                <h4 className="text-base font-bold text-emerald-950">Request Recorded!</h4>
                <p className="text-xs text-emerald-800 leading-relaxed">{bookingSuccess.message}</p>
                <div className="p-2.5 bg-white rounded-xl border border-emerald-200 text-xs font-mono text-emerald-900">
                  Booking Reference ID: {bookingSuccess.id}
                </div>
                <p className="text-[11px] text-emerald-700 italic">
                  Note: Provider confirmation is required before service schedule is finalized.
                </p>
                <button
                  onClick={() => setBookingCandidate(null)}
                  className="mt-2 text-xs font-bold bg-emerald-700 text-white px-5 py-2 rounded-xl hover:bg-emerald-800"
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleBookingSubmit} className="space-y-3 text-xs">
                {bookingError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700">
                    {bookingError}
                  </div>
                )}

                <div className="p-3 bg-amber-50 rounded-xl border border-amber-200/80 text-amber-900 text-[11px] leading-relaxed">
                  <strong>Notice:</strong> This is an introductory booking request. Since this provider is a research
                  candidate, confirmation is required before the visit is scheduled. No payment is taken upfront.
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Your Full Name *</label>
                  <input
                    type="text"
                    required
                    value={bookingForm.customer_name}
                    onChange={(e) => setBookingForm({ ...bookingForm, customer_name: e.target.value })}
                    placeholder="e.g. Anand Kumar"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Mobile Phone *</label>
                    <input
                      type="tel"
                      required
                      value={bookingForm.customer_phone}
                      onChange={(e) => setBookingForm({ ...bookingForm, customer_phone: e.target.value })}
                      placeholder="e.g. +91 98450 12345"
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Email Address</label>
                    <input
                      type="email"
                      value={bookingForm.customer_email}
                      onChange={(e) => setBookingForm({ ...bookingForm, customer_email: e.target.value })}
                      placeholder="e.g. anand@example.com"
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Service Address / Landmark</label>
                  <input
                    type="text"
                    value={bookingForm.customer_address}
                    onChange={(e) => setBookingForm({ ...bookingForm, customer_address: e.target.value })}
                    placeholder="e.g. Flat 302, Green Meadows, Kengeri Satellite Town"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Preferred Date</label>
                    <input
                      type="date"
                      value={bookingForm.preferred_date}
                      onChange={(e) => setBookingForm({ ...bookingForm, preferred_date: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Preferred Slot</label>
                    <select
                      value={bookingForm.preferred_time_slot}
                      onChange={(e) => setBookingForm({ ...bookingForm, preferred_time_slot: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20 bg-white"
                    >
                      <option>Morning (9 AM - 12 PM)</option>
                      <option>Afternoon (12 PM - 3 PM)</option>
                      <option>Evening (3 PM - 7 PM)</option>
                      <option>Flexible Timing</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Describe the Issue / Work Needed *</label>
                  <textarea
                    required
                    rows={3}
                    value={bookingForm.issue_description}
                    onChange={(e) => setBookingForm({ ...bookingForm, issue_description: e.target.value })}
                    placeholder="e.g. Kitchen sink pipe leakage, needs new washer or replacement..."
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#C8102E]/20"
                  />
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setBookingCandidate(null)}
                    className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={bookingSubmitting}
                    className="bg-[#C8102E] hover:bg-[#A50D25] disabled:opacity-50 text-white px-5 py-2 rounded-xl font-bold flex items-center gap-1.5 shadow-sm"
                  >
                    {bookingSubmitting ? (
                      'Recording...'
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" /> Submit Request
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
