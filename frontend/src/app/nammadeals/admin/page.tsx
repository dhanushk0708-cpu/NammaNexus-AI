'use client';

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Building2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  CreditCard,
  BarChart3,
  Search,
  Filter,
  Check,
  X,
  Clock,
  Eye,
  RotateCcw,
} from "lucide-react";
import {
  BusinessRegistrationRecord,
  CampaignRecord,
  AdvertiserPaymentRecord,
  getAdminRegistrations,
  reviewRegistration,
  getAdminCampaigns,
  reviewCampaign,
  updateBusinessStatus,
  getAdminPayments,
  verifyPayment,
} from "@/lib/nammadealsApi";

export default function AdminDashboardPage() {
  const [adminToken, setAdminToken] = useState("test-nammadeals-admin-secret-token");
  const [activeTab, setActiveTab] = useState<"registrations" | "campaigns" | "payments" | "analytics">("registrations");

  const [registrations, setRegistrations] = useState<BusinessRegistrationRecord[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [payments, setPayments] = useState<AdvertiserPaymentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Review state
  const [rejectModalTarget, setRejectModalTarget] = useState<{ type: "reg" | "camp"; id: string } | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [regs, camps, pays] = await Promise.all([
        getAdminRegistrations(adminToken).catch(() => []),
        getAdminCampaigns(adminToken).catch(() => []),
        getAdminPayments(adminToken).catch(() => []),
      ]);
      setRegistrations(regs);
      setCampaigns(camps);
      setPayments(pays);
    } catch (e: any) {
      setError(e.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [adminToken]);

  const handleApproveRegistration = async (reg: BusinessRegistrationRecord) => {
    try {
      const assignedOwner = `usr_${reg.contact_name.toLowerCase().replace(/\s+/g, "_")}_${Date.now().toString().slice(-4)}`;
      await reviewRegistration(reg.id, "APPROVE", adminToken, assignedOwner);
      await loadData();
    } catch (e: any) {
      alert(`Approval error: ${e.message}`);
    }
  };

  const handleRejectRegistration = async () => {
    if (!rejectModalTarget || !rejectionReason.trim()) return;
    try {
      if (rejectModalTarget.type === "reg") {
        await reviewRegistration(rejectModalTarget.id, "REJECT", adminToken, undefined, rejectionReason);
      } else {
        await reviewCampaign(rejectModalTarget.id, "REJECT", adminToken, rejectionReason);
      }
      setRejectModalTarget(null);
      setRejectionReason("");
      await loadData();
    } catch (e: any) {
      alert(`Rejection error: ${e.message}`);
    }
  };

  const handleApproveCampaign = async (campaignId: string) => {
    try {
      await reviewCampaign(campaignId, "APPROVE", adminToken);
      await loadData();
    } catch (e: any) {
      alert(`Campaign approval error: ${e.message}`);
    }
  };

  const handleVerifyPayment = async (paymentId: string, action: "VERIFY" | "FAIL") => {
    try {
      await verifyPayment(paymentId, action, adminToken, "Bank statement confirmed by administrator");
      await loadData();
    } catch (e: any) {
      alert(`Payment verification error: ${e.message}`);
    }
  };

  const verifiedPaymentsTotal = payments
    .filter((p) => p.verification_status === "VERIFIED")
    .reduce((acc, p) => acc + p.amount, 0);

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8 flex-1">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-amber-800 uppercase bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
              Staff Portal
            </span>
            <span className="text-xs text-slate-500 font-medium">NammaDeals Platform Control</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 mt-1">Administrative Center</h1>
        </div>

        {/* Admin Token configuration */}
        <div className="flex items-center gap-2 text-xs bg-slate-50 border border-slate-200 p-2 rounded-xl">
          <span className="text-slate-500 font-semibold">Admin Token:</span>
          <input
            type="password"
            value={adminToken}
            onChange={(e) => setAdminToken(e.target.value)}
            className="font-mono bg-white border border-slate-300 rounded px-2 py-1 text-slate-800 text-xs w-48"
          />
          <button
            onClick={loadData}
            className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded text-xs"
          >
            Authenticate
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-xs text-red-800 font-semibold">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6 text-sm font-bold">
        <button
          onClick={() => setActiveTab("registrations")}
          className={`pb-3.5 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "registrations"
              ? "border-[#C8102E] text-[#C8102E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Building2 className="w-4 h-4" />
          <span>Business Registrations</span>
          {registrations.filter((r) => r.status === "PENDING").length > 0 && (
            <span className="text-[10px] bg-amber-100 text-amber-800 px-2 py-0.2 rounded-full font-black">
              {registrations.filter((r) => r.status === "PENDING").length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("campaigns")}
          className={`pb-3.5 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "campaigns"
              ? "border-[#C8102E] text-[#C8102E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Campaign Approvals</span>
          {campaigns.filter((c) => c.approval_status === "PENDING_APPROVAL").length > 0 && (
            <span className="text-[10px] bg-red-100 text-[#C8102E] px-2 py-0.2 rounded-full font-black">
              {campaigns.filter((c) => c.approval_status === "PENDING_APPROVAL").length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("payments")}
          className={`pb-3.5 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "payments"
              ? "border-[#C8102E] text-[#C8102E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <CreditCard className="w-4 h-4" />
          <span>Payments Verification</span>
          {payments.filter((p) => p.verification_status === "PENDING").length > 0 && (
            <span className="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.2 rounded-full font-black">
              {payments.filter((p) => p.verification_status === "PENDING").length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("analytics")}
          className={`pb-3.5 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "analytics"
              ? "border-[#C8102E] text-[#C8102E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Platform Analytics</span>
        </button>
      </div>

      {/* TAB 1: REGISTRATIONS */}
      {activeTab === "registrations" && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">Submitted Business Applications</h3>
            <button onClick={loadData} className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1">
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>

          {registrations.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center text-xs text-slate-500">
              No business registrations on file.
            </div>
          ) : (
            <div className="overflow-x-auto bg-white border border-slate-200 rounded-2xl shadow-xs">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                  <tr>
                    <th className="p-3.5">Business Name</th>
                    <th className="p-3.5">Category</th>
                    <th className="p-3.5">Contact</th>
                    <th className="p-3.5">Area / PIN</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {registrations.map((reg) => (
                    <tr key={reg.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="p-3.5 font-bold text-slate-900">{reg.business_name}</td>
                      <td className="p-3.5">{reg.category}</td>
                      <td className="p-3.5">
                        <div className="font-semibold text-slate-800">{reg.contact_name}</div>
                        <div className="text-[11px] text-slate-500">{reg.email} • {reg.phone}</div>
                      </td>
                      <td className="p-3.5">{reg.area} ({reg.pincode})</td>
                      <td className="p-3.5">
                        <span
                          className={`text-[10px] font-black px-2 py-0.5 rounded-full uppercase border ${
                            reg.status === "APPROVED"
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                              : reg.status === "REJECTED"
                              ? "bg-red-50 text-red-800 border-red-200"
                              : "bg-amber-50 text-amber-800 border-amber-200"
                          }`}
                        >
                          {reg.status}
                        </span>
                      </td>
                      <td className="p-3.5 text-right space-x-1.5">
                        {reg.status === "PENDING" && (
                          <>
                            <button
                              onClick={() => handleApproveRegistration(reg)}
                              className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => {
                                setRejectModalTarget({ type: "reg", id: reg.id });
                                setRejectionReason("");
                              }}
                              className="px-2.5 py-1.5 bg-red-100 hover:bg-red-200 text-red-800 font-bold rounded-lg text-xs"
                            >
                              Reject
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* TAB 2: CAMPAIGNS */}
      {activeTab === "campaigns" && (
        <section className="space-y-4">
          <h3 className="text-base font-bold text-slate-900">Campaigns Review Queue</h3>

          {campaigns.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center text-xs text-slate-500">
              No campaigns pending review.
            </div>
          ) : (
            <div className="overflow-x-auto bg-white border border-slate-200 rounded-2xl shadow-xs">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                  <tr>
                    <th className="p-3.5">Campaign Name</th>
                    <th className="p-3.5">Type & Strategy</th>
                    <th className="p-3.5">Dates</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {campaigns.map((camp) => (
                    <tr key={camp.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="p-3.5">
                        <div className="font-bold text-slate-900">{camp.name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">ID: {camp.id.slice(0, 8)}...</div>
                      </td>
                      <td className="p-3.5">
                        <span className="font-semibold text-slate-800">{camp.campaign_type}</span>
                        <div className="text-[11px] text-slate-500">
                          {camp.targeting_strategy} ({camp.targeting_radius_km} km)
                        </div>
                      </td>
                      <td className="p-3.5 text-slate-600">
                        {new Date(camp.start_date).toLocaleDateString()} — {new Date(camp.end_date).toLocaleDateString()}
                      </td>
                      <td className="p-3.5">
                        <span
                          className={`text-[10px] font-black px-2 py-0.5 rounded-full uppercase border ${
                            camp.approval_status === "APPROVED"
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                              : camp.approval_status === "REJECTED"
                              ? "bg-red-50 text-red-800 border-red-200"
                              : "bg-amber-50 text-amber-800 border-amber-200"
                          }`}
                        >
                          {camp.approval_status}
                        </span>
                      </td>
                      <td className="p-3.5 text-right space-x-1.5">
                        {camp.approval_status === "PENDING_APPROVAL" && (
                          <>
                            <button
                              onClick={() => handleApproveCampaign(camp.id)}
                              className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => {
                                setRejectModalTarget({ type: "camp", id: camp.id });
                                setRejectionReason("");
                              }}
                              className="px-2.5 py-1.5 bg-red-100 hover:bg-red-200 text-red-800 font-bold rounded-lg text-xs"
                            >
                              Reject
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* TAB 3: PAYMENTS */}
      {activeTab === "payments" && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">Advertiser Deposit & Payment Records</h3>
            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full">
              Verified Revenue: ₹{verifiedPaymentsTotal.toLocaleString()}
            </span>
          </div>

          {payments.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center text-xs text-slate-500">
              No payments submitted yet.
            </div>
          ) : (
            <div className="overflow-x-auto bg-white border border-slate-200 rounded-2xl shadow-xs">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                  <tr>
                    <th className="p-3.5">Transaction ID</th>
                    <th className="p-3.5">Amount</th>
                    <th className="p-3.5">Method</th>
                    <th className="p-3.5">Date</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Verification</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {payments.map((pay) => (
                    <tr key={pay.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="p-3.5 font-bold text-slate-900">{pay.transaction_id}</td>
                      <td className="p-3.5 font-bold text-emerald-700">₹{pay.amount.toLocaleString()}</td>
                      <td className="p-3.5">{pay.payment_method}</td>
                      <td className="p-3.5 text-slate-500">{new Date(pay.payment_date).toLocaleDateString()}</td>
                      <td className="p-3.5">
                        <span
                          className={`text-[10px] font-black px-2 py-0.5 rounded-full uppercase border font-sans ${
                            pay.verification_status === "VERIFIED"
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                              : pay.verification_status === "FAILED"
                              ? "bg-red-50 text-red-800 border-red-200"
                              : "bg-amber-50 text-amber-800 border-amber-200"
                          }`}
                        >
                          {pay.verification_status}
                        </span>
                      </td>
                      <td className="p-3.5 text-right space-x-1.5 font-sans">
                        {pay.verification_status === "PENDING" && (
                          <>
                            <button
                              onClick={() => handleVerifyPayment(pay.id, "VERIFY")}
                              className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs"
                            >
                              Verify
                            </button>
                            <button
                              onClick={() => handleVerifyPayment(pay.id, "FAIL")}
                              className="px-2.5 py-1.5 bg-red-100 hover:bg-red-200 text-red-800 font-bold rounded-lg text-xs"
                            >
                              Fail
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* TAB 4: PLATFORM ANALYTICS */}
      {activeTab === "analytics" && (
        <section className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
              <span className="text-xs font-semibold text-slate-500">Registered Businesses</span>
              <div className="text-3xl font-black text-slate-900 mt-1">{registrations.length}</div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
              <span className="text-xs font-semibold text-slate-500">Active Campaigns</span>
              <div className="text-3xl font-black text-emerald-600 mt-1">
                {campaigns.filter((c) => c.is_active).length}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
              <span className="text-xs font-semibold text-slate-500">Total Campaigns</span>
              <div className="text-3xl font-black text-slate-900 mt-1">{campaigns.length}</div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
              <span className="text-xs font-semibold text-slate-500">Platform Ad Revenue</span>
              <div className="text-3xl font-black text-[#C8102E] mt-1">
                ₹{verifiedPaymentsTotal.toLocaleString()}
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-2">
            <h4 className="text-sm font-bold text-slate-900">Geospatial Distribution</h4>
            <p className="text-xs text-slate-500 leading-relaxed">
              Campaigns are serving across Koramangala, Indiranagar, Jayanagar, Malleshwaram, Whitefield, and city-wide Bengaluru BBMP wards with deterministic frequency caps and radius boundary checks.
            </p>
          </div>
        </section>
      )}

      {/* REJECT MODAL */}
      {rejectModalTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900">Specify Rejection Reason</h3>
            <textarea
              required
              rows={3}
              placeholder="e.g. Incomplete business address or non-compliant promotion terms..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={handleRejectRegistration}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs"
              >
                Confirm Rejection
              </button>
              <button
                onClick={() => setRejectModalTarget(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
