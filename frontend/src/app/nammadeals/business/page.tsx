'use client';

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Building2,
  PlusCircle,
  Clock,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  CreditCard,
  BarChart3,
  MapPin,
  Tag,
  ShieldCheck,
  ChevronRight,
  Sparkles,
  ExternalLink,
  Store,
} from "lucide-react";
import {
  BusinessRecord,
  CampaignRecord,
  getMyBusinesses,
  getBusinessCampaigns,
  submitBusinessRegistration,
  recordAdvertiserPayment,
  redeemCouponInStore,
  getBusinessAnalytics,
  BusinessAnalytics,
  CouponRedemptionResult,
} from "@/lib/nammadealsApi";

export default function BusinessDashboardPage() {
  const [userId] = useState("usr_campaign_owner_1");
  const [businesses, setBusinesses] = useState<BusinessRecord[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState<BusinessRecord | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Registration Form State
  const [showRegisterForm, setShowRegisterForm] = useState(false);
  const [regSuccess, setRegSuccess] = useState(false);
  const [regData, setRegData] = useState({
    business_name: "",
    category: "Restaurant",
    contact_name: "",
    email: "",
    phone: "",
    address: "",
    area: "Koramangala",
    pincode: "560034",
    google_maps_url: "",
    description: "",
  });

  // Payment Form State
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [paymentData, setPaymentData] = useState({
    amount: 2500,
    transaction_id: "",
    payment_method: "UPI" as const,
  });

  // Analytics State
  const [analytics, setAnalytics] = useState<BusinessAnalytics | null>(null);

  // In-Store Redemption State
  const [redeemCode, setRedeemCode] = useState("");
  const [redeemNotes, setRedeemNotes] = useState("");
  const [redeemLoading, setRedeemLoading] = useState(false);
  const [redeemResult, setRedeemResult] = useState<CouponRedemptionResult | null>(null);
  const [redeemError, setRedeemError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const bizList = await getMyBusinesses(userId);
      setBusinesses(bizList);
      if (bizList.length > 0) {
        const activeBiz = bizList[0];
        setSelectedBusiness(activeBiz);
        const [campList, bizAnalytics] = await Promise.all([
          getBusinessCampaigns(activeBiz.id, userId).catch(() => []),
          getBusinessAnalytics(activeBiz.id, userId).catch(() => null),
        ]);
        setCampaigns(campList);
        setAnalytics(bizAnalytics);
      } else {
        setSelectedBusiness(null);
        setCampaigns([]);
        setAnalytics(null);
      }
    } catch (e: any) {
      setError(e.message || "Failed to load business profile");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await submitBusinessRegistration({
        business_name: regData.business_name,
        category: regData.category,
        contact_name: regData.contact_name,
        email: regData.email,
        phone: regData.phone,
        address: regData.address,
        area: regData.area,
        pincode: regData.pincode,
        city: "Bengaluru",
        google_maps_url: regData.google_maps_url.trim() || undefined,
        description: regData.description || undefined,
      });
      setRegSuccess(true);
      setShowRegisterForm(false);
      await loadData();
    } catch (e: any) {
      alert(`Registration failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRedeemCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBusiness || !redeemCode.trim()) return;
    try {
      setRedeemLoading(true);
      setRedeemError(null);
      setRedeemResult(null);

      const result = await redeemCouponInStore(
        selectedBusiness.id,
        redeemCode.trim().toUpperCase(),
        userId,
        redeemNotes.trim() || undefined
      );
      setRedeemResult(result);
      setRedeemCode("");
      setRedeemNotes("");
      await loadData();
    } catch (e: any) {
      setRedeemError(e.message || "Failed to verify and redeem coupon.");
    } finally {
      setRedeemLoading(false);
    }
  };

  const handlePaymentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBusiness) return;
    try {
      await recordAdvertiserPayment(
        selectedBusiness.id,
        {
          amount: Number(paymentData.amount),
          currency: "INR",
          transaction_id: paymentData.transaction_id || `UPI_${Date.now()}`,
          payment_method: paymentData.payment_method,
          payment_date: new Date().toISOString(),
        },
        userId
      );
      alert("Payment recorded! Awaiting admin verification.");
      setShowPaymentForm(false);
    } catch (e: any) {
      alert(`Payment failed: ${e.message}`);
    }
  };

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8 flex-1">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-[#C8102E] uppercase bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
              Merchant Portal
            </span>
            <span className="text-xs text-slate-500 font-medium">NammaDeals Business Platform</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 mt-1">Local Business Dashboard</h1>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/nammadeals"
            className="text-xs font-bold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3.5 py-2 rounded-xl transition-colors"
          >
            Citizen Offers View
          </Link>
          <Link
            href="/nammadeals/admin"
            className="text-xs font-bold text-[#C8102E] hover:text-white hover:bg-[#C8102E] bg-red-50 border border-red-200 px-3.5 py-2 rounded-xl transition-all"
          >
            Admin Center
          </Link>
        </div>
      </div>

      {/* Registration notice */}
      {regSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 text-xs text-emerald-800 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold text-sm">Registration Submitted Successfully!</p>
            <p>
              Your local business application has been submitted and is currently in <span className="font-bold">PENDING</span> status. An administrator will review your physical shop location and verify your business.
            </p>
          </div>
        </div>
      )}

      {/* No Business registered state */}
      {!loading && businesses.length === 0 && !showRegisterForm && (
        <div className="bg-white border border-slate-200 rounded-3xl p-10 text-center space-y-4 max-w-lg mx-auto shadow-xs">
          <div className="w-12 h-12 bg-red-50 text-[#C8102E] rounded-2xl flex items-center justify-center mx-auto">
            <Building2 className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900">No Business Registered Yet</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Register your physical store, restaurant, or service shop on NammaNexus. Once approved by our team, your shop can be featured in civic rewards and local promotions.
            </p>
          </div>
          <button
            onClick={() => setShowRegisterForm(true)}
            className="bg-[#C8102E] hover:bg-[#A60C24] text-white text-xs font-bold px-5 py-3 rounded-xl shadow-md transition-all inline-flex items-center gap-2"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Register Your Business</span>
          </button>
        </div>
      )}

      {/* REGISTRATION FORM MODAL */}
      {showRegisterForm && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-5 max-w-2xl mx-auto shadow-sm">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-lg font-bold text-slate-900">Register a Local Physical Business</h3>
            <p className="text-xs text-slate-500">
              Provide verified physical shop location, contact details, and Google Maps link for Bengaluru.
            </p>
          </div>

          <form onSubmit={handleRegisterSubmit} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Business Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Koramangala Craft Cafe"
                  value={regData.business_name}
                  onChange={(e) => setRegData({ ...regData, business_name: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Category</label>
                <select
                  value={regData.category}
                  onChange={(e) => setRegData({ ...regData, category: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                >
                  <option value="Restaurant">Restaurant / Food</option>
                  <option value="Cafe">Cafe & Bakery</option>
                  <option value="Retail">Retail & Groceries</option>
                  <option value="Services">Local Services & Repair</option>
                  <option value="Fitness">Fitness & Healthcare</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Contact Person Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rajesh Kumar"
                  value={regData.contact_name}
                  onChange={(e) => setRegData({ ...regData, contact_name: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Contact Email</label>
                <input
                  type="email"
                  required
                  placeholder="rajesh@business.in"
                  value={regData.email}
                  onChange={(e) => setRegData({ ...regData, email: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Phone Number (10 digits)</label>
                <input
                  type="text"
                  required
                  placeholder="9876543210"
                  value={regData.phone}
                  onChange={(e) => setRegData({ ...regData, phone: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Area / Locality in Bengaluru</label>
                <input
                  type="text"
                  required
                  placeholder="Koramangala 4th Block"
                  value={regData.area}
                  onChange={(e) => setRegData({ ...regData, area: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">PIN Code (6 digits)</label>
                <input
                  type="text"
                  required
                  pattern="^\d{6}$"
                  placeholder="560034"
                  value={regData.pincode}
                  onChange={(e) => setRegData({ ...regData, pincode: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-blue-600" />
                  <span>Google Maps Share Link</span>
                </label>
                <input
                  type="url"
                  placeholder="https://maps.app.goo.gl/... or https://maps.google.com/?q=..."
                  value={regData.google_maps_url}
                  onChange={(e) => setRegData({ ...regData, google_maps_url: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-mono text-xs"
                />
                <span className="text-[10px] text-slate-400 block">
                  Paste the Google Maps share link of your physical store so citizens can find your shop.
                </span>
              </div>

              <div className="space-y-1 sm:col-span-2">
                <label className="font-semibold text-slate-700">Full Physical Shop Address</label>
                <textarea
                  required
                  rows={2}
                  placeholder="123, 80ft Road, near Sony World Signal, Koramangala 4th Block..."
                  value={regData.address}
                  onChange={(e) => setRegData({ ...regData, address: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>
            </div>

            <div className="flex items-center gap-3 pt-3 border-t border-slate-100">
              <button
                type="submit"
                className="bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold px-5 py-2.5 rounded-xl shadow-xs"
              >
                Submit Registration for Review
              </button>
              <button
                type="button"
                onClick={() => setShowRegisterForm(false)}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-4 py-2.5 rounded-xl"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* BUSINESS DASHBOARD VIEW */}
      {selectedBusiness && (
        <div className="space-y-8">
          {/* Status & Overview Bar */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  {selectedBusiness.category}
                </span>
                <span
                  className={`text-[11px] font-black px-2.5 py-0.5 rounded-full uppercase border ${
                    selectedBusiness.status === "APPROVED"
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                      : selectedBusiness.status === "SUSPENDED"
                      ? "bg-red-50 text-red-800 border-red-200"
                      : "bg-amber-50 text-amber-800 border-amber-200"
                  }`}
                >
                  {selectedBusiness.status}
                </span>
              </div>
              <h2 className="text-2xl font-black text-slate-900">{selectedBusiness.name}</h2>
              <p className="text-xs text-slate-500 flex items-center gap-1.5">
                <Store className="w-3.5 h-3.5 text-slate-400" />
                <span>{selectedBusiness.address}, {selectedBusiness.area} — {selectedBusiness.pincode}</span>
              </p>

              {/* Google Maps Store Location Link */}
              {selectedBusiness.google_maps_store_url && (
                <div className="pt-1">
                  <a
                    href={selectedBusiness.google_maps_store_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>View Shop on Google Maps</span>
                  </a>
                </div>
              )}
            </div>

            {/* Merchant Payment Action */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setShowPaymentForm(true)}
                className="text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2.5 rounded-xl border border-slate-200 flex items-center gap-1.5"
              >
                <CreditCard className="w-4 h-4 text-emerald-600" />
                <span>Record Payment / Deposit</span>
              </button>
            </div>
          </div>

          {/* Business KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-slate-900">
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs">
              <span className="text-xs text-slate-500 font-semibold">Active Campaigns</span>
              <div className="text-2xl font-black text-emerald-600 mt-1">
                {campaigns.filter((c) => c.is_active).length}
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs">
              <span className="text-xs text-slate-500 font-semibold">Customer Claims</span>
              <div className="text-2xl font-black text-amber-600 mt-1">
                {analytics ? analytics.claims : 0}
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs">
              <span className="text-xs text-slate-500 font-semibold">Verified Redemptions</span>
              <div className="text-2xl font-black text-emerald-600 mt-1">
                {analytics ? analytics.redemptions : 0}
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs">
              <span className="text-xs text-slate-500 font-semibold">Verification</span>
              <div className="text-sm font-extrabold text-slate-800 mt-2">
                {selectedBusiness.status === "APPROVED" ? "Verified Partner" : "Under Review"}
              </div>
            </div>
          </div>

          {/* IN-STORE CITIZEN COUPON REDEMPTION BOX */}
          <div className="bg-white border-2 border-dashed border-red-200 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <div className="inline-flex items-center gap-1.5 text-xs font-bold text-[#C8102E] bg-red-50 border border-red-200 px-2.5 py-0.5 rounded-full mb-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Merchant POS / Cashier Desk</span>
                </div>
                <h3 className="text-base font-extrabold text-slate-900">Verify & Redeem Citizen Coupon</h3>
                <p className="text-xs text-slate-500">
                  Verify a customer&apos;s unique coupon code in real-time. Prevents duplicate claims and records audit trail.
                </p>
              </div>
            </div>

            <form onSubmit={handleRedeemCoupon} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2 space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Citizen Unique Coupon Code</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. FILTER20-AB12CD34"
                    value={redeemCode}
                    onChange={(e) => setRedeemCode(e.target.value.toUpperCase())}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono text-sm font-bold text-slate-900 tracking-wider uppercase focus:ring-2 focus:ring-red-400 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Audit Note / Bill Ref</label>
                  <input
                    type="text"
                    placeholder="e.g. Bill #4092"
                    value={redeemNotes}
                    onChange={(e) => setRedeemNotes(e.target.value)}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-slate-400">
                  Redemption immediately locks the coupon code across all platform nodes.
                </span>
                <button
                  type="submit"
                  disabled={redeemLoading || !redeemCode.trim()}
                  className={`px-5 py-2.5 rounded-xl font-bold text-xs shadow-xs transition-all flex items-center gap-1.5 ${
                    redeemLoading || !redeemCode.trim()
                      ? "bg-slate-200 text-slate-400 cursor-not-allowed"
                      : "bg-[#C8102E] hover:bg-[#A60C24] text-white"
                  }`}
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>{redeemLoading ? "Verifying..." : "Verify & Redeem"}</span>
                </button>
              </div>
            </form>

            {/* Redemption Success Feedback */}
            {redeemResult && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 space-y-2 animate-in fade-in duration-200">
                <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <span>{redeemResult.message}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs text-slate-700">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Code</span>
                    <span className="font-mono font-bold text-slate-900">{redeemResult.unique_coupon_code}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Offer</span>
                    <span className="font-semibold text-slate-900">{redeemResult.offer_title}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Discount</span>
                    <span className="font-extrabold text-[#C8102E]">{redeemResult.discount_summary}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Timestamp</span>
                    <span className="font-medium text-slate-600">
                      {new Date(redeemResult.redeemed_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Redemption Failure Feedback */}
            {redeemError && (
              <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-3 text-red-800 text-xs font-semibold animate-in fade-in duration-200">
                <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
                <span>Verification Failed: {redeemError}</span>
              </div>
            )}
          </div>

          {/* RECORD PAYMENT MODAL */}
          {showPaymentForm && (
            <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 max-w-md shadow-md">
              <h3 className="text-base font-bold text-slate-900">Record Advertiser Payment</h3>
              <p className="text-xs text-slate-500">Record an advertising deposit or promotion fee.</p>

              <form onSubmit={handlePaymentSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Amount (INR)</label>
                  <input
                    type="number"
                    min={100}
                    value={paymentData.amount}
                    onChange={(e) => setPaymentData({ ...paymentData, amount: Number(e.target.value) })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Payment Method</label>
                  <select
                    value={paymentData.payment_method}
                    onChange={(e: any) => setPaymentData({ ...paymentData, payment_method: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                  >
                    <option value="UPI">UPI (Google Pay / PhonePe / Paytm)</option>
                    <option value="CARD">Credit / Debit Card</option>
                    <option value="NETBANKING">Netbanking</option>
                    <option value="BANK_TRANSFER">Direct Bank Transfer</option>
                  </select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Transaction / Reference ID</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. UPI_TXN_9876543210"
                    value={paymentData.transaction_id}
                    onChange={(e) => setPaymentData({ ...paymentData, transaction_id: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono"
                  />
                </div>
                <div className="flex gap-2 pt-2">
                  <button type="submit" className="flex-1 bg-emerald-600 text-white font-bold py-2 rounded-xl">
                    Submit Payment Reference
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowPaymentForm(false)}
                    className="px-3 py-2 bg-slate-100 rounded-xl"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* ACTIVE CAMPAIGNS (READ-ONLY CURATED PROMOTIONS) */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Active Advertising Campaigns</h3>
                <p className="text-xs text-slate-500">
                  Advertisements on NammaNexus are curated and managed centrally by platform administrators to guarantee high quality and civic relevance.
                </p>
              </div>
              <div className="text-xs font-semibold text-slate-500 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-xl">
                Managed by Admin Desk
              </div>
            </div>

            {campaigns.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center text-xs text-slate-500 space-y-2">
                <p>No active campaigns running for this business currently.</p>
                <p className="text-slate-400">
                  Once your business registration is approved, contact the NammaDeals Admin team to schedule a targeted promotion.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {campaigns.map((camp) => (
                  <div
                    key={camp.id}
                    className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                  >
                    <div className="space-y-1 max-w-xl">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[10px] font-black px-2 py-0.5 rounded border uppercase ${
                            camp.status === "ACTIVE" || camp.is_active
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                              : camp.status === "PAUSED"
                              ? "bg-amber-50 text-amber-800 border-amber-200"
                              : "bg-slate-100 text-slate-600 border-slate-200"
                          }`}
                        >
                          {camp.status || (camp.is_active ? "ACTIVE" : "PAUSED")}
                        </span>

                        <span className="text-xs text-slate-400">
                          Radius: {camp.targeting_radius_km} km • Strategy: {camp.targeting_strategy}
                        </span>
                      </div>

                      <h4 className="text-base font-bold text-slate-900">{camp.name}</h4>
                      <p className="text-xs text-slate-500">
                        Validity: {new Date(camp.start_date).toLocaleDateString()} — {new Date(camp.end_date).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="text-right">
                      <span className="text-xs font-bold text-slate-500 bg-slate-50 border border-slate-200 px-3 py-1 rounded-lg">
                        Admin-Managed
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
