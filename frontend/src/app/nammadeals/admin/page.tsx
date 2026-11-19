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
  PlusCircle,
  ExternalLink,
  MapPin,
  Upload,
  Image as ImageIcon,
  Play,
  Pause,
  Edit,
  Trash2,
  Target,
} from "lucide-react";
import {
  BusinessRegistrationRecord,
  BusinessRecord,
  CampaignRecord,
  AdvertiserPaymentRecord,
  getAdminRegistrations,
  getAdminBusinesses,
  reviewRegistration,
  getAdminCampaigns,
  reviewCampaign,
  updateBusinessStatus,
  getAdminPayments,
  verifyPayment,
  getAdminPlatformAnalytics,
  AdminPlatformAnalytics,
  adminCreateCampaign,
  adminUpdateCampaign,
  adminSetCampaignStatus,
  adminUpdateBusinessLocation,
  uploadCampaignImage,
  AdminCampaignCreateData,
} from "@/lib/nammadealsApi";

export default function AdminDashboardPage() {
  const [adminToken, setAdminToken] = useState("test-nammadeals-admin-secret-token");
  const [activeTab, setActiveTab] = useState<"campaigns" | "registrations" | "payments" | "analytics">("campaigns");

  const [registrations, setRegistrations] = useState<BusinessRegistrationRecord[]>([]);
  const [approvedBusinesses, setApprovedBusinesses] = useState<BusinessRecord[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [payments, setPayments] = useState<AdvertiserPaymentRecord[]>([]);
  const [platformAnalytics, setPlatformAnalytics] = useState<AdminPlatformAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Review & Modal States
  const [rejectModalTarget, setRejectModalTarget] = useState<{ type: "reg" | "camp"; id: string } | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  // Create Campaign Modal State
  const [showCreateCampaignModal, setShowCreateCampaignModal] = useState(false);
  const [createCampaignLoading, setCreateCampaignLoading] = useState(false);
  const [campaignFormData, setCampaignFormData] = useState<AdminCampaignCreateData>({
    business_id: "",
    name: "",
    description: "",
    campaign_type: "COUPON",
    offer_title: "",
    offer_description: "",
    discount_type: "PERCENTAGE",
    discount_value: 20,
    coupon_code: "CIVIC20",
    advertisement_image_url: "",
    targeting_mode: "BOTH",
    targeting_radius_km: 3.5,
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
    max_claims: 500,
    status: "ACTIVE",
    terms_and_conditions: "Valid on all purchases. One claim per citizen.",
  });

  // Edit Campaign Modal State
  const [editingCampaign, setEditingCampaign] = useState<CampaignRecord | null>(null);
  const [editFormData, setEditFormData] = useState<Partial<AdminCampaignCreateData>>({});

  // Image Upload State
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);

  // Location Verification Dialog State
  const [verifyingBusiness, setVerifyingBusiness] = useState<BusinessRegistrationRecord | null>(null);
  const [locationForm, setLocationForm] = useState({
    google_maps_url: "",
    latitude: 12.9716,
    longitude: 77.5946,
    area: "",
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [regs, bizList, camps, pays, stats] = await Promise.all([
        getAdminRegistrations(adminToken).catch(() => []),
        getAdminBusinesses(adminToken, "APPROVED").catch(() => []),
        getAdminCampaigns(adminToken).catch(() => []),
        getAdminPayments(adminToken).catch(() => []),
        getAdminPlatformAnalytics(adminToken).catch(() => null),
      ]);
      setRegistrations(regs);
      setApprovedBusinesses(bizList);
      setCampaigns(camps);
      setPayments(pays);
      setPlatformAnalytics(stats);

      // Preselect first approved business in form if empty
      if (bizList.length > 0 && !campaignFormData.business_id) {
        setCampaignFormData((prev) => ({ ...prev, business_id: bizList[0].id }));
      }
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

  const handleVerifyPayment = async (payId: string, action: "VERIFY" | "FAIL") => {
    try {
      await verifyPayment(payId, action, adminToken);
      await loadData();
    } catch (e: any) {
      alert(`Payment verification error: ${e.message}`);
    }
  };

  // Image Upload Handler
  const handleImageFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploadingImage(true);
      const res = await uploadCampaignImage(file, adminToken);
      setCampaignFormData((prev) => ({ ...prev, advertisement_image_url: res.image_url }));
      setImagePreviewUrl(res.image_url);
    } catch (err: any) {
      alert(`Image upload error: ${err.message}`);
    } finally {
      setUploadingImage(false);
    }
  };

  const handleEditImageFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploadingImage(true);
      const res = await uploadCampaignImage(file, adminToken);
      setEditFormData((prev) => ({ ...prev, advertisement_image_url: res.image_url }));
    } catch (err: any) {
      alert(`Image upload error: ${err.message}`);
    } finally {
      setUploadingImage(false);
    }
  };

  // Create Campaign Submit
  const handleCreateCampaignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!campaignFormData.business_id) {
      alert("Please select an approved business.");
      return;
    }
    try {
      setCreateCampaignLoading(true);
      await adminCreateCampaign(
        {
          ...campaignFormData,
          start_date: new Date(campaignFormData.start_date).toISOString(),
          end_date: new Date(campaignFormData.end_date).toISOString(),
          discount_value: Number(campaignFormData.discount_value),
          targeting_radius_km: Number(campaignFormData.targeting_radius_km),
          max_claims: Number(campaignFormData.max_claims),
        },
        adminToken
      );
      setShowCreateCampaignModal(false);
      setImagePreviewUrl(null);
      await loadData();
    } catch (err: any) {
      alert(`Failed to create campaign: ${err.message}`);
    } finally {
      setCreateCampaignLoading(false);
    }
  };

  // Edit Campaign Submit
  const handleEditCampaignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCampaign) return;
    try {
      setCreateCampaignLoading(true);
      await adminUpdateCampaign(
        editingCampaign.id,
        {
          ...editFormData,
          discount_value: editFormData.discount_value != null ? Number(editFormData.discount_value) : undefined,
          targeting_radius_km: editFormData.targeting_radius_km != null ? Number(editFormData.targeting_radius_km) : undefined,
        },
        adminToken
      );
      setEditingCampaign(null);
      await loadData();
    } catch (err: any) {
      alert(`Failed to update campaign: ${err.message}`);
    } finally {
      setCreateCampaignLoading(false);
    }
  };

  // Quick Status Toggle
  const handleSetCampaignStatus = async (
    campaignId: string,
    status: "DRAFT" | "ACTIVE" | "PAUSED" | "EXPIRED" | "DEACTIVATED"
  ) => {
    try {
      await adminSetCampaignStatus(campaignId, status, adminToken);
      await loadData();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  // Location Verification Submit
  const handleSaveLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyingBusiness) return;
    try {
      await adminUpdateBusinessLocation(
        verifyingBusiness.id,
        {
          google_maps_url: locationForm.google_maps_url || undefined,
          latitude: Number(locationForm.latitude),
          longitude: Number(locationForm.longitude),
          area: locationForm.area || undefined,
        },
        adminToken
      );
      setVerifyingBusiness(null);
      await loadData();
    } catch (err: any) {
      alert(`Failed to update business location: ${err.message}`);
    }
  };

  const getFullImageUrl = (url?: string | null) => {
    if (!url) return null;
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    const base = process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") || "http://localhost:8000";
    return `${base}${url}`;
  };

  const verifiedPaymentsTotal = payments
    .filter((p) => p.verification_status === "VERIFIED")
    .reduce((sum, p) => sum + p.amount, 0);

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8 flex-1">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-white uppercase bg-[#C8102E] px-2 py-0.5 rounded-full">
              Central Administration
            </span>
            <span className="text-xs text-slate-500 font-semibold">NammaDeals Platform Operations</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 mt-1">NammaDeals Advertising Operations Center</h1>
          <p className="text-xs text-slate-500">
            Centrally curate, verify physical shop locations, and create location-targeted advertisement campaigns.
          </p>
        </div>

        {/* Global Action & Token Setup */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setShowCreateCampaignModal(true)}
            className="px-4 py-2.5 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center gap-2"
          >
            <PlusCircle className="w-4 h-4" />
            <span>+ CREATE CAMPAIGN</span>
          </button>

          <div className="flex items-center gap-2 text-xs bg-slate-50 border border-slate-200 p-1.5 rounded-xl">
            <span className="text-slate-400 font-semibold px-1">Admin Key:</span>
            <input
              type="password"
              value={adminToken}
              onChange={(e) => setAdminToken(e.target.value)}
              className="bg-white border border-slate-300 rounded px-2 py-1 text-slate-800 text-xs w-36 font-mono"
            />
            <button
              onClick={loadData}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-900 text-white font-bold rounded text-xs"
            >
              Sync
            </button>
          </div>
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
          onClick={() => setActiveTab("campaigns")}
          className={`pb-3.5 flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "campaigns"
              ? "border-[#C8102E] text-[#C8102E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Advertisement Campaigns</span>
          <span className="text-[10px] bg-red-100 text-[#C8102E] px-2 py-0.2 rounded-full font-black">
            {campaigns.length}
          </span>
        </button>

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

      {/* TAB 1: CAMPAIGNS (ADMIN-CURATED ADVERTISEMENTS) */}
      {activeTab === "campaigns" && (
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-slate-900">Advertisement Campaigns Inventory</h3>
              <p className="text-xs text-slate-500">
                Centrally created campaigns with visual promotional banners and geographic targeting.
              </p>
            </div>
            <button
              onClick={() => setShowCreateCampaignModal(true)}
              className="px-3.5 py-2 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-xs rounded-xl shadow-xs flex items-center gap-1.5 self-start sm:self-auto"
            >
              <PlusCircle className="w-4 h-4" />
              <span>+ Create Campaign</span>
            </button>
          </div>

          {campaigns.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-3xl p-10 text-center space-y-3">
              <div className="w-12 h-12 bg-red-50 text-[#C8102E] rounded-2xl flex items-center justify-center mx-auto">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h4 className="text-base font-bold text-slate-900">No Advertising Campaigns Yet</h4>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Platform admins have exclusive authority to create and publish advertisements. Click below to launch your first civic advertisement.
              </p>
              <button
                onClick={() => setShowCreateCampaignModal(true)}
                className="px-4 py-2 bg-[#C8102E] text-white font-bold text-xs rounded-xl shadow-xs"
              >
                + Create First Campaign
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto bg-white border border-slate-200 rounded-2xl shadow-xs">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                  <tr>
                    <th className="p-3.5">Banner</th>
                    <th className="p-3.5">Campaign & Business</th>
                    <th className="p-3.5">Targeting Mode & Radius</th>
                    <th className="p-3.5">Claims & Redemptions</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {campaigns.map((camp) => {
                    const bannerUrl = getFullImageUrl(camp.advertisement_image_url);
                    const isActive = camp.status === "ACTIVE" || camp.is_active;

                    return (
                      <tr key={camp.id} className="hover:bg-slate-50/70 transition-colors">
                        {/* Banner Thumbnail */}
                        <td className="p-3.5">
                          {bannerUrl ? (
                            <div className="w-20 h-12 rounded-lg overflow-hidden bg-slate-100 border border-slate-200 shrink-0">
                              <img src={bannerUrl} alt={camp.name} className="w-full h-full object-cover" />
                            </div>
                          ) : (
                            <div className="w-20 h-12 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400">
                              <ImageIcon className="w-4 h-4" />
                            </div>
                          )}
                        </td>

                        {/* Campaign and Business */}
                        <td className="p-3.5">
                          <div className="font-bold text-slate-900 text-sm">{camp.name}</div>
                          <div className="text-xs text-slate-500 font-medium">
                            {camp.business_name || "Business"} ({camp.business_area || "Bengaluru"})
                          </div>
                          {camp.store_maps_url && (
                            <a
                              href={camp.store_maps_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:underline mt-0.5"
                            >
                              <ExternalLink className="w-3 h-3" />
                              <span>Store on Maps</span>
                            </a>
                          )}
                        </td>

                        {/* Targeting Mode */}
                        <td className="p-3.5">
                          <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200 mb-1">
                            <Target className="w-3 h-3 text-slate-500" />
                            <span>{camp.targeting_mode || "BOTH"}</span>
                          </div>
                          <div className="text-xs text-slate-600 font-semibold">
                            Radius: {camp.targeting_radius_km} km
                          </div>
                          <div className="text-[11px] text-slate-400">
                            {new Date(camp.start_date).toLocaleDateString()} — {new Date(camp.end_date).toLocaleDateString()}
                          </div>
                        </td>

                        {/* Claims */}
                        <td className="p-3.5">
                          <div className="font-bold text-slate-800">
                            {camp.current_claims || 0} / {camp.max_claims || 500} claimed
                          </div>
                          <div className="text-[11px] text-emerald-600 font-semibold">
                            {camp.redemptions_count || 0} redeemed
                          </div>
                        </td>

                        {/* Status */}
                        <td className="p-3.5">
                          <span
                            className={`text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase border ${
                              isActive
                                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                : camp.status === "PAUSED"
                                ? "bg-amber-50 text-amber-800 border-amber-200"
                                : camp.status === "DEACTIVATED"
                                ? "bg-red-50 text-red-800 border-red-200"
                                : "bg-slate-100 text-slate-600 border-slate-200"
                            }`}
                          >
                            {camp.status || (isActive ? "ACTIVE" : "PAUSED")}
                          </span>
                        </td>

                        {/* Actions */}
                        <td className="p-3.5 text-right space-x-1.5 whitespace-nowrap">
                          {/* Pause / Activate */}
                          {isActive ? (
                            <button
                              onClick={() => handleSetCampaignStatus(camp.id, "PAUSED")}
                              className="px-2.5 py-1.5 bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold rounded-lg text-xs inline-flex items-center gap-1"
                            >
                              <Pause className="w-3 h-3" />
                              <span>Pause</span>
                            </button>
                          ) : (
                            <button
                              onClick={() => handleSetCampaignStatus(camp.id, "ACTIVE")}
                              className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs inline-flex items-center gap-1"
                            >
                              <Play className="w-3 h-3" />
                              <span>Activate</span>
                            </button>
                          )}

                          {/* Edit */}
                          <button
                            onClick={() => {
                              setEditingCampaign(camp);
                              setEditFormData({
                                name: camp.name,
                                advertisement_image_url: camp.advertisement_image_url || "",
                                targeting_mode: camp.targeting_mode || "BOTH",
                                targeting_radius_km: camp.targeting_radius_km,
                              });
                            }}
                            className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg text-xs inline-flex items-center gap-1"
                          >
                            <Edit className="w-3 h-3" />
                            <span>Edit</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* TAB 2: REGISTRATIONS & PHYSICAL STORE LOCATION */}
      {activeTab === "registrations" && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900">Submitted Business Applications</h3>
              <p className="text-xs text-slate-500">
                Verify merchant physical shop locations, coordinates, and Google Maps links.
              </p>
            </div>
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
                    <th className="p-3.5">Business & Contact</th>
                    <th className="p-3.5">Physical Shop Address</th>
                    <th className="p-3.5">Google Maps Store Link</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {registrations.map((reg) => (
                    <tr key={reg.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="p-3.5">
                        <div className="font-bold text-slate-900 text-sm">{reg.business_name}</div>
                        <div className="text-[11px] text-slate-500">{reg.category}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {reg.contact_name} • {reg.phone}
                        </div>
                      </td>

                      <td className="p-3.5 max-w-xs">
                        <div className="text-slate-800 font-medium">{reg.address}</div>
                        <div className="text-slate-500 text-[11px]">
                          {reg.area}, {reg.city || "Bengaluru"} — {reg.pincode}
                        </div>
                        {reg.latitude && reg.longitude && (
                          <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                            Coords: {reg.latitude.toFixed(4)}, {reg.longitude.toFixed(4)}
                          </div>
                        )}
                      </td>

                      <td className="p-3.5">
                        {reg.google_maps_store_url || reg.google_maps_url ? (
                          <a
                            href={reg.google_maps_store_url || reg.google_maps_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg text-xs font-bold transition-colors"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span>Open in Maps</span>
                          </a>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Not Provided</span>
                        )}
                      </td>

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

                      <td className="p-3.5 text-right space-x-1.5 whitespace-nowrap">
                        <button
                          onClick={() => {
                            setVerifyingBusiness(reg);
                            setLocationForm({
                              google_maps_url: reg.google_maps_url || "",
                              latitude: reg.latitude || 12.9716,
                              longitude: reg.longitude || 77.5946,
                              area: reg.area,
                            });
                          }}
                          className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg text-xs inline-flex items-center gap-1"
                        >
                          <MapPin className="w-3 h-3 text-blue-600" />
                          <span>Verify Location</span>
                        </button>

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
              <div className="text-3xl font-black text-slate-900 mt-1">
                {platformAnalytics ? platformAnalytics.total_businesses : registrations.length}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
              <span className="text-xs font-semibold text-slate-500">Active Campaigns</span>
              <div className="text-3xl font-black text-emerald-600 mt-1">
                {platformAnalytics ? platformAnalytics.active_campaigns : campaigns.filter((c) => c.is_active).length}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
              <span className="text-xs font-semibold text-slate-500">Total Campaigns</span>
              <div className="text-3xl font-black text-slate-900 mt-1">
                {platformAnalytics ? platformAnalytics.total_campaigns : campaigns.length}
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
              <span className="text-xs font-semibold text-slate-500">Verified Platform Revenue</span>
              <div className="text-3xl font-black text-[#C8102E] mt-1">
                ₹{(platformAnalytics ? platformAnalytics.total_revenue_inr : verifiedPaymentsTotal).toLocaleString()}
              </div>
            </div>
          </div>

          {platformAnalytics && (
            <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="space-y-0.5">
                  <div className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-800 bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 rounded-full">
                    <BarChart3 className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Cross-Platform Conversion Aggregates</span>
                  </div>
                  <h3 className="text-base font-extrabold text-slate-900">Total Event Engagement Funnel</h3>
                </div>
                <div className="text-xs font-bold text-slate-500">
                  Pending Revenue: <span className="text-amber-600">₹{platformAnalytics.pending_revenue_inr.toLocaleString()}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Impressions</span>
                  <div className="text-2xl font-black text-slate-900 mt-1">{platformAnalytics.total_impressions}</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Clicks</span>
                  <div className="text-2xl font-black text-slate-900 mt-1">{platformAnalytics.total_clicks}</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Claims</span>
                  <div className="text-2xl font-black text-amber-600 mt-1">{platformAnalytics.total_claims}</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Redemptions</span>
                  <div className="text-2xl font-black text-emerald-600 mt-1">{platformAnalytics.total_redemptions}</div>
                </div>
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold block">Overall CTR</span>
                  <div className="text-2xl font-black text-indigo-600 mt-1">{platformAnalytics.overall_ctr_percentage}%</div>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* CREATE CAMPAIGN MODAL (ADMIN ONLY) */}
      {showCreateCampaignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 sm:p-8 space-y-5 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">+ Create Advertisement Campaign</h3>
                <p className="text-xs text-slate-500">
                  Platform admins configure campaigns directly for approved local businesses.
                </p>
              </div>
              <button
                onClick={() => setShowCreateCampaignModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCampaignSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Business Selector */}
                <div className="space-y-1 sm:col-span-2">
                  <label className="font-semibold text-slate-700">Target Business (Approved)</label>
                  <select
                    required
                    value={campaignFormData.business_id}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, business_id: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  >
                    <option value="">-- Select an Approved Business --</option>
                    {approvedBusinesses.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name} ({b.area} • {b.category})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Campaign Name */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Campaign Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Indiranagar Pour-over Special"
                    value={campaignFormData.name}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, name: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  >
                  </input>
                </div>

                {/* Promotion Type */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Promotion Type</label>
                  <select
                    value={campaignFormData.campaign_type}
                    onChange={(e: any) => setCampaignFormData({ ...campaignFormData, campaign_type: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  >
                    <option value="COUPON">Coupon / Promo Code</option>
                    <option value="SCRATCH_CARD">Predetermined Scratch Card</option>
                  </select>
                </div>

                {/* Offer Title */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Offer Title</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Flat 25% Off on All Nitro Cold Brews"
                    value={campaignFormData.offer_title}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, offer_title: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  />
                </div>

                {/* Redeem Code */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Base Coupon / Redeem Code</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. NITRO25"
                    value={campaignFormData.coupon_code}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, coupon_code: e.target.value.toUpperCase() })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-900"
                  />
                </div>

                {/* Discount Type & Value */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Discount Type</label>
                  <select
                    value={campaignFormData.discount_type}
                    onChange={(e: any) => setCampaignFormData({ ...campaignFormData, discount_type: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  >
                    <option value="PERCENTAGE">Percentage (%)</option>
                    <option value="FLAT">Flat Amount (₹)</option>
                    <option value="FREEBIE">Freebie / BOGO</option>
                    <option value="REWARD">Predetermined Reward</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Discount Value</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={campaignFormData.discount_value}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, discount_value: Number(e.target.value) })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  />
                </div>

                {/* Targeting Mode */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Location Targeting Mode</label>
                  <select
                    value={campaignFormData.targeting_mode}
                    onChange={(e: any) => setCampaignFormData({ ...campaignFormData, targeting_mode: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-bold"
                  >
                    <option value="BOTH">Both (SpotFix Complaint + Citizen Profile)</option>
                    <option value="COMPLAINT_ONLY">SpotFix Complaint Location Only</option>
                    <option value="PROFILE_ONLY">Citizen Profile Location Only</option>
                  </select>
                </div>

                {/* Targeting Radius */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Targeting Radius (km)</label>
                  <input
                    type="number"
                    step="0.5"
                    min={0.5}
                    max={30}
                    value={campaignFormData.targeting_radius_km}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, targeting_radius_km: Number(e.target.value) })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  />
                </div>

                {/* Dates */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Start Date</label>
                  <input
                    type="date"
                    required
                    value={campaignFormData.start_date}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, start_date: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">End Date</label>
                  <input
                    type="date"
                    required
                    value={campaignFormData.end_date}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, end_date: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  />
                </div>

                {/* Max Claims & Initial Status */}
                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Max Claims Inventory</label>
                  <input
                    type="number"
                    min={1}
                    value={campaignFormData.max_claims}
                    onChange={(e) => setCampaignFormData({ ...campaignFormData, max_claims: Number(e.target.value) })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Initial Status</label>
                  <select
                    value={campaignFormData.status}
                    onChange={(e: any) => setCampaignFormData({ ...campaignFormData, status: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-bold"
                  >
                    <option value="ACTIVE">ACTIVE (Published Immediately)</option>
                    <option value="DRAFT">DRAFT (Saved for Later)</option>
                    <option value="PAUSED">PAUSED</option>
                  </select>
                </div>
              </div>

              {/* Advertisement Promotional Banner Image Upload */}
              <div className="space-y-2 p-4 bg-slate-50 rounded-2xl border border-slate-200">
                <label className="font-bold text-slate-900 flex items-center gap-1.5">
                  <ImageIcon className="w-4 h-4 text-[#C8102E]" />
                  <span>Visual Advertisement Banner Image (JPEG / PNG / WebP)</span>
                </label>

                {campaignFormData.advertisement_image_url ? (
                  <div className="space-y-2">
                    <div className="relative w-full h-36 rounded-xl overflow-hidden bg-slate-200 border border-slate-300">
                      <img
                        src={getFullImageUrl(campaignFormData.advertisement_image_url) || ""}
                        alt="Banner Preview"
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-500 font-mono text-[11px] truncate max-w-xs">
                        {campaignFormData.advertisement_image_url}
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          setCampaignFormData((prev) => ({ ...prev, advertisement_image_url: "" }));
                          setImagePreviewUrl(null);
                        }}
                        className="text-red-600 hover:underline font-bold text-xs"
                      >
                        Remove Image
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={handleImageFileChange}
                      disabled={uploadingImage}
                      className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-[#C8102E] file:text-white hover:file:bg-[#A60C24] file:cursor-pointer"
                    />
                    {uploadingImage && <span className="text-[11px] text-amber-700 font-bold">Uploading banner...</span>}
                  </div>
                )}
              </div>

              {/* Offer Description */}
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Offer Description & Conditions</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Show your SpotFix civic participation receipt to redeem this exclusive discount..."
                  value={campaignFormData.offer_description}
                  onChange={(e) => setCampaignFormData({ ...campaignFormData, offer_description: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateCampaignModal(false)}
                  className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createCampaignLoading}
                  className="px-6 py-2.5 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold rounded-xl shadow-md"
                >
                  {createCampaignLoading ? "Publishing..." : "Publish Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT CAMPAIGN MODAL */}
      {editingCampaign && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900">Edit Campaign: {editingCampaign.name}</h3>

            <form onSubmit={handleEditCampaignSubmit} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Campaign Name</label>
                <input
                  type="text"
                  value={editFormData.name || ""}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Targeting Mode</label>
                  <select
                    value={editFormData.targeting_mode || "BOTH"}
                    onChange={(e: any) => setEditFormData({ ...editFormData, targeting_mode: e.target.value })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-bold"
                  >
                    <option value="BOTH">BOTH Locations</option>
                    <option value="COMPLAINT_ONLY">Complaint Only</option>
                    <option value="PROFILE_ONLY">Profile Only</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Radius (km)</label>
                  <input
                    type="number"
                    step="0.5"
                    min={0.5}
                    value={editFormData.targeting_radius_km || 3.5}
                    onChange={(e) => setEditFormData({ ...editFormData, targeting_radius_km: Number(e.target.value) })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                  />
                </div>
              </div>

              {/* Advertisement image */}
              <div className="space-y-1">
                <label className="font-semibold text-slate-700 block">Replace Banner Image</label>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleEditImageFileChange}
                  className="w-full text-xs text-slate-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-slate-800 file:text-white"
                />
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="submit"
                  disabled={createCampaignLoading}
                  className="px-4 py-2 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold rounded-xl text-xs"
                >
                  Save Changes
                </button>
                <button
                  type="button"
                  onClick={() => setEditingCampaign(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* VERIFY / EDIT LOCATION MODAL */}
      {verifyingBusiness && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900">
              Verify Physical Location: {verifyingBusiness.business_name}
            </h3>

            <form onSubmit={handleSaveLocation} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Google Maps Link</label>
                <input
                  type="url"
                  placeholder="https://maps.app.goo.gl/... or https://maps.google.com/?q=..."
                  value={locationForm.google_maps_url}
                  onChange={(e) => setLocationForm({ ...locationForm, google_maps_url: e.target.value })}
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-mono text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Latitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={locationForm.latitude}
                    onChange={(e) => setLocationForm({ ...locationForm, latitude: Number(e.target.value) })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Longitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={locationForm.longitude}
                    onChange={(e) => setLocationForm({ ...locationForm, longitude: Number(e.target.value) })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-mono text-xs"
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs"
                >
                  Verify & Save Location
                </button>
                <button
                  type="button"
                  onClick={() => setVerifyingBusiness(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
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
