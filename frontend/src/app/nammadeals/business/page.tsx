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
  Play,
  Pause,
  Send,
  CreditCard,
  BarChart3,
  MapPin,
  Tag,
  ShieldCheck,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import {
  BusinessRecord,
  CampaignRecord,
  getMyBusinesses,
  getBusinessCampaigns,
  submitBusinessRegistration,
  createCampaign,
  createOffer,
  submitCampaignForApproval,
  toggleCampaignActive,
  recordAdvertiserPayment,
  redeemCouponInStore,
  getBusinessAnalytics,
  BusinessAnalytics,
  CouponRedemptionResult,
} from "@/lib/nammadealsApi";

export default function BusinessDashboardPage() {
  const [userId, setUserId] = useState("usr_campaign_owner_1");
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
    description: "",
  });

  // Campaign Creation State
  const [showCreateCampaign, setShowCreateCampaign] = useState(false);
  const [campData, setCampData] = useState({
    name: "",
    campaign_type: "DISCOUNT" as const,
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
    targeting_strategy: "RADIUS" as const,
    targeting_radius_km: 5.0,
    offer_title: "",
    discount_type: "PERCENTAGE" as const,
    discount_value: 20,
    coupon_code: "DEAL20",
    terms: "Valid on dine-in orders above ₹500.",
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
          getBusinessCampaigns(activeBiz.id, userId),
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

  const handleRedeemCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBusiness || !redeemCode.trim()) return;
    try {
      setRedeemLoading(true);
      setRedeemError(null);
      setRedeemResult(null);
      const res = await redeemCouponInStore(
        selectedBusiness.id,
        userId,
        redeemCode.trim(),
        redeemNotes.trim() || undefined
      );
      setRedeemResult(res);
      setRedeemCode("");
      setRedeemNotes("");
      // Refresh analytics & campaigns
      const updatedAnalytics = await getBusinessAnalytics(selectedBusiness.id, userId).catch(() => null);
      if (updatedAnalytics) setAnalytics(updatedAnalytics);
    } catch (err: any) {
      setRedeemError(err.message || "Redemption failed");
    } finally {
      setRedeemLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [userId]);

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await submitBusinessRegistration({
        ...regData,
        city: "Bengaluru",
      });
      setRegSuccess(true);
      setShowRegisterForm(false);
    } catch (e: any) {
      alert(`Registration failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCampaignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBusiness) return;
    try {
      setLoading(true);
      // 1. Create campaign
      const camp = await createCampaign(
        selectedBusiness.id,
        {
          name: campData.name,
          campaign_type: campData.campaign_type,
          start_date: new Date(campData.start_date).toISOString(),
          end_date: new Date(campData.end_date).toISOString(),
          targeting_strategy: campData.targeting_strategy,
          targeting_radius_km: Number(campData.targeting_radius_km),
          priority: 15,
        },
        userId
      );

      // 2. Add offer
      await createOffer(
        camp.id,
        {
          title: campData.offer_title,
          discount_type: campData.discount_type,
          discount_value: Number(campData.discount_value),
          terms_and_conditions: campData.terms,
          valid_from: new Date(campData.start_date).toISOString(),
          valid_until: new Date(campData.end_date).toISOString(),
          offer_type: "COUPON",
          coupon_code: campData.coupon_code,
          max_redemptions: 100,
        },
        userId
      );

      setShowCreateCampaign(false);
      await loadData();
    } catch (e: any) {
      alert(`Error creating campaign: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitForApproval = async (campaignId: string) => {
    try {
      await submitCampaignForApproval(campaignId, userId);
      await loadData();
    } catch (e: any) {
      alert(`Approval submission failed: ${e.message}`);
    }
  };

  const handleToggleActive = async (campaignId: string, currentActive: boolean) => {
    try {
      await toggleCampaignActive(campaignId, !currentActive, userId);
      await loadData();
    } catch (e: any) {
      alert(`Failed to toggle campaign: ${e.message}`);
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

        {/* Demo User Switcher */}
        <div className="flex items-center gap-2 text-xs bg-slate-50 border border-slate-200 p-2 rounded-xl">
          <span className="text-slate-500 font-semibold">Owner ID:</span>
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="font-mono bg-white border border-slate-300 rounded px-2 py-1 text-slate-800 text-xs w-44"
          />
          <button
            onClick={loadData}
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-900 text-white font-bold rounded text-xs"
          >
            Switch
          </button>
        </div>
      </div>

      {/* Registration notice */}
      {regSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 text-xs text-emerald-800 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold text-sm">Registration Submitted Successfully!</p>
            <p>
              Your local business application has been submitted and is currently in <span className="font-bold">PENDING</span> status. An administrator will review your address and verify your business before advertising is enabled.
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
              Register your local store, cafe, or business on NammaNexus to promote targeted civic rewards and offers to nearby residents.
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
            <h3 className="text-lg font-bold text-slate-900">Register a Local Business</h3>
            <p className="text-xs text-slate-500">Provide verified business and contact information for Bengaluru.</p>
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
                <label className="font-semibold text-slate-700">Area / Locality</label>
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

              <div className="space-y-1 sm:col-span-2">
                <label className="font-semibold text-slate-700">Full Store Address</label>
                <textarea
                  required
                  rows={2}
                  placeholder="123, 80ft Road, near Sony World Signal..."
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
            <div className="space-y-1">
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
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                {selectedBusiness.address}, {selectedBusiness.area} — {selectedBusiness.pincode}
              </p>
            </div>

            {/* Quick Actions */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setShowCreateCampaign(true)}
                disabled={selectedBusiness.status !== "APPROVED"}
                className={`text-xs font-bold px-4 py-2.5 rounded-xl shadow-xs flex items-center gap-1.5 ${
                  selectedBusiness.status === "APPROVED"
                    ? "bg-[#C8102E] hover:bg-[#A60C24] text-white"
                    : "bg-slate-100 text-slate-400 cursor-not-allowed"
                }`}
              >
                <PlusCircle className="w-4 h-4" />
                <span>New Campaign</span>
              </button>

              <button
                onClick={() => setShowPaymentForm(true)}
                className="text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2.5 rounded-xl border border-slate-200 flex items-center gap-1.5"
              >
                <CreditCard className="w-4 h-4 text-emerald-600" />
                <span>Add Payment</span>
              </button>
            </div>
          </div>

          {/* Business KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-slate-900">
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs">
              <span className="text-xs text-slate-500 font-semibold">Total Campaigns</span>
              <div className="text-2xl font-black mt-1">{campaigns.length}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs">
              <span className="text-xs text-slate-500 font-semibold">Active Campaigns</span>
              <div className="text-2xl font-black text-emerald-600 mt-1">
                {campaigns.filter((c) => c.is_active).length}
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs">
              <span className="text-xs text-slate-500 font-semibold">Pending Approval</span>
              <div className="text-2xl font-black text-amber-600 mt-1">
                {campaigns.filter((c) => c.approval_status === "PENDING_APPROVAL").length}
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
                  Verify a citizen&apos;s unique coupon code in real-time. Prevents duplicate claims and records audit trail.
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

          {/* FULL-LIFECYCLE CAMPAIGN PERFORMANCE ANALYTICS */}
          {analytics && (
            <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="space-y-0.5">
                  <div className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-800 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full">
                    <BarChart3 className="w-3.5 h-3.5 text-amber-600" />
                    <span>Real-Time Campaign Performance</span>
                  </div>
                  <h3 className="text-base font-extrabold text-slate-900">Conversion Funnel & Analytics</h3>
                </div>
                <div className="text-xs font-bold text-slate-500">
                  Verified Ad Spend: <span className="text-[#C8102E]">₹{analytics.verified_payments_total.toLocaleString()}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 text-center">
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-3">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Impressions</span>
                  <div className="text-xl font-black text-slate-900 mt-1">{analytics.impressions}</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-3">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Clicks</span>
                  <div className="text-xl font-black text-slate-900 mt-1">{analytics.clicks}</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-3">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Claims</span>
                  <div className="text-xl font-black text-amber-600 mt-1">{analytics.claims}</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-3">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Redemptions</span>
                  <div className="text-xl font-black text-emerald-600 mt-1">{analytics.redemptions}</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-3">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">CTR</span>
                  <div className="text-xl font-black text-indigo-600 mt-1">{analytics.overall_ctr_percentage}%</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-3">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Conversion</span>
                  <div className="text-xl font-black text-[#C8102E] mt-1">{analytics.overall_redemption_rate_percentage}%</div>
                </div>
              </div>
            </div>
          )}

          {/* CREATE CAMPAIGN MODAL */}
          {showCreateCampaign && (
            <div className="bg-white border border-red-200 rounded-3xl p-6 sm:p-8 space-y-5 shadow-md">
              <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Create Advertising Campaign</h3>
                  <p className="text-xs text-slate-500">Configure promotion details, targeting radius, and offer.</p>
                </div>
                <button
                  onClick={() => setShowCreateCampaign(false)}
                  className="text-xs font-bold text-slate-400 hover:text-slate-600"
                >
                  Close
                </button>
              </div>

              <form onSubmit={handleCreateCampaignSubmit} className="space-y-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Campaign Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Weekend Monsoon Special"
                      value={campData.name}
                      onChange={(e) => setCampData({ ...campData, name: e.target.value })}
                      className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Targeting Strategy</label>
                    <select
                      value={campData.targeting_strategy}
                      onChange={(e: any) => setCampData({ ...campData, targeting_strategy: e.target.value })}
                      className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                    >
                      <option value="RADIUS">Local Radius (Geo-Targeted)</option>
                      <option value="WARD">Ward & Neighborhood</option>
                      <option value="CITYWIDE">City-Wide (Bengaluru)</option>
                      <option value="ONLINE">Online Offer</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Targeting Radius (km)</label>
                    <input
                      type="number"
                      min={0.5}
                      max={25}
                      step={0.5}
                      value={campData.targeting_radius_km}
                      onChange={(e) => setCampData({ ...campData, targeting_radius_km: Number(e.target.value) })}
                      className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Start Date</label>
                    <input
                      type="date"
                      required
                      value={campData.start_date}
                      onChange={(e) => setCampData({ ...campData, start_date: e.target.value })}
                      className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">End Date</label>
                    <input
                      type="date"
                      required
                      value={campData.end_date}
                      onChange={(e) => setCampData({ ...campData, end_date: e.target.value })}
                      className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                    />
                  </div>

                  {/* Initial Offer details */}
                  <div className="sm:col-span-2 pt-2 border-t border-slate-100">
                    <h4 className="font-bold text-slate-900 text-sm mb-2">Initial Promotional Offer</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="space-y-1">
                        <label className="font-semibold text-slate-700">Offer Title</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. 25% Off on All Coffees"
                          value={campData.offer_title}
                          onChange={(e) => setCampData({ ...campData, offer_title: e.target.value })}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="font-semibold text-slate-700">Discount Value (%)</label>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={campData.discount_value}
                          onChange={(e) => setCampData({ ...campData, discount_value: Number(e.target.value) })}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="font-semibold text-slate-700">Coupon Code</label>
                        <input
                          type="text"
                          required
                          value={campData.coupon_code}
                          onChange={(e) => setCampData({ ...campData, coupon_code: e.target.value.toUpperCase() })}
                          className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono font-bold"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-3">
                  <button
                    type="submit"
                    className="bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold px-5 py-2.5 rounded-xl shadow-xs"
                  >
                    Save Campaign Draft
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateCampaign(false)}
                    className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-4 py-2.5 rounded-xl"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* RECORD PAYMENT MODAL */}
          {showPaymentForm && (
            <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 max-w-md shadow-md">
              <h3 className="text-base font-bold text-slate-900">Record Advertiser Payment</h3>
              <p className="text-xs text-slate-500">Record an advertising deposit or campaign promotion fee.</p>

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

          {/* CAMPAIGNS LIST */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Advertising Campaigns</h3>

            {campaigns.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center text-xs text-slate-500">
                No campaigns created yet. Click &quot;New Campaign&quot; to configure your first promotion.
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
                            camp.approval_status === "APPROVED"
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                              : camp.approval_status === "PENDING_APPROVAL"
                              ? "bg-amber-50 text-amber-800 border-amber-200"
                              : camp.approval_status === "REJECTED"
                              ? "bg-red-50 text-red-800 border-red-200"
                              : "bg-slate-100 text-slate-600 border-slate-200"
                          }`}
                        >
                          {camp.approval_status}
                        </span>

                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            camp.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          {camp.is_active ? "● ACTIVE & SERVING" : "○ PAUSED"}
                        </span>

                        <span className="text-xs text-slate-400">
                          Strategy: {camp.targeting_strategy} ({camp.targeting_radius_km} km)
                        </span>
                      </div>

                      <h4 className="text-base font-bold text-slate-900">{camp.name}</h4>
                      <p className="text-xs text-slate-500">
                        Validity: {new Date(camp.start_date).toLocaleDateString()} — {new Date(camp.end_date).toLocaleDateString()}
                      </p>
                      {camp.rejection_reason && (
                        <p className="text-xs text-red-600 font-semibold bg-red-50 p-2 rounded border border-red-100">
                          Rejection Reason: {camp.rejection_reason}
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      {camp.approval_status === "DRAFT" || camp.approval_status === "REJECTED" ? (
                        <button
                          onClick={() => handleSubmitForApproval(camp.id)}
                          className="text-xs font-bold bg-[#C8102E] hover:bg-[#A60C24] text-white px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-2xs"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Submit for Approval</span>
                        </button>
                      ) : null}

                      {camp.approval_status === "APPROVED" && (
                        <button
                          onClick={() => handleToggleActive(camp.id, camp.is_active)}
                          className={`text-xs font-bold px-3.5 py-2 rounded-xl flex items-center gap-1.5 transition-colors ${
                            camp.is_active
                              ? "bg-amber-100 hover:bg-amber-200 text-amber-900"
                              : "bg-emerald-600 hover:bg-emerald-700 text-white"
                          }`}
                        >
                          {camp.is_active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                          <span>{camp.is_active ? "Pause Serving" : "Activate Ads"}</span>
                        </button>
                      )}
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
