/**
 * NammaDeals API Client and TypeScript Definitions
 * Integrates directly with the backend FastAPI endpoints at /api/v1/nammadeals
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface PromotionOfferItem {
  id: string;
  title: string;
  description?: string | null;
  promotional_image_url?: string | null;
  discount_type: "PERCENTAGE" | "FLAT" | "FREEBIE" | "REWARD";
  discount_value: number;
  terms_and_conditions?: string | null;
  valid_until: string;
  offer_type: "COUPON" | "SCRATCH_CARD" | "INSTANT_DISCOUNT";
  coupon_code?: string | null;
  scratch_card_config?: {
    win_headline?: string;
    min_discount?: number;
    max_discount?: number;
    reward_text?: string;
  } | null;
}

export interface PromotionItem {
  campaign_id: string;
  campaign_name: string;
  campaign_type: "DISCOUNT" | "COUPON" | "SCRATCH_CARD" | "AWARENESS";
  business_name: string;
  business_category: string;
  business_area: string;
  advertisement_image_url?: string | null;
  store_maps_url?: string | null;
  matched_location_source: "COMPLAINT" | "PROFILE" | "NEARBY" | "CITYWIDE" | "ONLINE" | "INVENTORY";
  distance_km?: number | null;
  offers: PromotionOfferItem[];
}

export interface PromotionSelectionResponse {
  promotions: PromotionItem[];
  total_selected: number;
  location_sources_evaluated: string[];
  policy_applied: string;
}

export interface BusinessRegistrationData {
  business_name: string;
  description?: string;
  category: string;
  contact_name: string;
  email: string;
  phone: string;
  address: string;
  city?: string;
  area: string;
  pincode: string;
  google_maps_url?: string;
  logo_url?: string;
  latitude?: number;
  longitude?: number;
}

export interface BusinessRegistrationRecord extends BusinessRegistrationData {
  id: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  google_maps_store_url?: string | null;
  rejection_reason?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BusinessRecord {
  id: string;
  owner_user_id: string;
  registration_id?: string | null;
  name: string;
  description?: string | null;
  category: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  area: string;
  pincode: string;
  google_maps_url?: string | null;
  logo_url?: string | null;
  google_maps_store_url?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "SUSPENDED";
  verified_at?: string | null;
  verified_by?: string | null;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignRecord {
  id: string;
  business_id: string;
  name: string;
  description?: string | null;
  campaign_type: "DISCOUNT" | "COUPON" | "SCRATCH_CARD" | "AWARENESS";
  advertisement_image_url?: string | null;
  targeting_mode?: "PROFILE_ONLY" | "COMPLAINT_ONLY" | "BOTH";
  status?: "DRAFT" | "ACTIVE" | "PAUSED" | "EXPIRED" | "DEACTIVATED";
  business_name?: string | null;
  business_area?: string | null;
  store_maps_url?: string | null;
  offers_count?: number | null;
  max_claims?: number | null;
  current_claims?: number | null;
  redemptions_count?: number | null;
  start_date: string;
  end_date: string;
  approval_status: "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "SUSPENDED";
  is_active: boolean;
  targeting_strategy: "RADIUS" | "WARD" | "CITYWIDE" | "ONLINE";
  targeting_radius_km: number;
  latitude?: number | null;
  longitude?: number | null;
  priority: number;
  frequency_limit_per_user: number;
  placement_config?: any;
  rejection_reason?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdvertiserPaymentRecord {
  id: string;
  business_id: string;
  campaign_id?: string | null;
  amount: number;
  currency: string;
  transaction_id: string;
  payment_method: "UPI" | "CARD" | "NETBANKING" | "BANK_TRANSFER";
  payment_date: string;
  verification_status: "PENDING" | "VERIFIED" | "FAILED" | "REFUNDED";
  admin_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimedCoupon {
  id: string;
  campaign_id: string;
  campaign_name: string;
  business_name: string;
  business_area: string;
  offer_title: string;
  coupon_code: string;
  discount_label: string;
  valid_until: string;
  claimed_at: string;
  is_used: boolean;
}

// Client-side claimed coupons persistence
export const getClaimedCoupons = (): ClaimedCoupon[] => {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem("nammanexus_claimed_coupons");
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

export const saveClaimedCoupon = (coupon: ClaimedCoupon): void => {
  if (typeof window === "undefined") return;
  try {
    const existing = getClaimedCoupons();
    if (!existing.some((c) => c.coupon_code === coupon.coupon_code && c.campaign_id === coupon.campaign_id)) {
      existing.unshift(coupon);
      localStorage.setItem("nammanexus_claimed_coupons", JSON.stringify(existing));
    }
  } catch (e) {
    console.error("Failed to save claimed coupon", e);
  }
};

// --- Promotion Engine APIs ---

export async function selectPromotions(
  request: {
    citizen_user_id?: string;
    location_policy?: "COMBINED" | "PROFILE_ONLY" | "COMPLAINT_ONLY" | "PREFER_COMPLAINT" | "PREFER_PROFILE";
    profile_location?: {
      state?: string;
      city?: string;
      area?: string;
      pincode?: string;
      latitude?: number;
      longitude?: number;
    };
    complaint_location?: {
      latitude?: number;
      longitude?: number;
      area?: string;
      ward?: string;
    };
    limit?: number;
  },
  citizenUserId?: string
): Promise<PromotionSelectionResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (citizenUserId) {
    headers["X-User-ID"] = citizenUserId;
  }

  const res = await fetch(`${API_BASE}/nammadeals/promotions/select`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      citizen_user_id: citizenUserId,
      location_policy: request.location_policy || "COMBINED",
      profile_location: request.profile_location,
      complaint_location: request.complaint_location,
      limit: request.limit || 3,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to load promotions" }));
    throw new Error(err.detail || "Failed to load promotions");
  }

  return res.json();
}

export async function recordPromotionEvent(
  data: {
    event_type: "IMPRESSION" | "CLICK" | "CLAIM" | "REDEMPTION";
    campaign_id: string;
    offer_id?: string;
    location_source?: string;
    idempotency_key?: string;
    event_metadata?: any;
  },
  citizenUserId?: string
): Promise<any> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (citizenUserId) {
    headers["X-User-ID"] = citizenUserId;
  }

  const res = await fetch(`${API_BASE}/nammadeals/promotions/events`, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    // Non-critical tracking error
    return null;
  }

  return res.json();
}

export async function getPromotionDetails(campaignId: string): Promise<PromotionItem> {
  const res = await fetch(`${API_BASE}/nammadeals/promotions/${campaignId}`);
  if (!res.ok) {
    throw new Error("Failed to fetch promotion details");
  }
  return res.json();
}

// --- Business Registration & Management APIs ---

export async function submitBusinessRegistration(
  data: BusinessRegistrationData
): Promise<BusinessRegistrationRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/registrations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Registration submission failed" }));
    throw new Error(err.detail || "Registration submission failed");
  }
  return res.json();
}

export async function getMyBusinesses(userId: string): Promise<BusinessRecord[]> {
  const res = await fetch(`${API_BASE}/nammadeals/businesses/me`, {
    headers: { "X-User-ID": userId },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch owned businesses");
  }
  return res.json();
}

export async function getBusinessCampaigns(businessId: string, userId: string): Promise<CampaignRecord[]> {
  const res = await fetch(`${API_BASE}/nammadeals/businesses/${businessId}/campaigns`, {
    headers: { "X-User-ID": userId },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch campaigns for business");
  }
  return res.json();
}

export async function createCampaign(
  businessId: string,
  data: any,
  userId: string
): Promise<CampaignRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/businesses/${businessId}/campaigns`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": userId,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Campaign creation failed" }));
    throw new Error(err.detail || "Campaign creation failed");
  }
  return res.json();
}

export async function createOffer(
  campaignId: string,
  data: any,
  userId: string
): Promise<PromotionOfferItem> {
  const res = await fetch(`${API_BASE}/nammadeals/campaigns/${campaignId}/offers`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": userId,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Offer creation failed" }));
    throw new Error(err.detail || "Offer creation failed");
  }
  return res.json();
}

export async function submitCampaignForApproval(
  campaignId: string,
  userId: string
): Promise<CampaignRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/campaigns/${campaignId}/submit-approval`, {
    method: "POST",
    headers: { "X-User-ID": userId },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to submit campaign for approval" }));
    throw new Error(err.detail || "Failed to submit campaign for approval");
  }
  return res.json();
}

export async function toggleCampaignActive(
  campaignId: string,
  isActive: boolean,
  userId: string
): Promise<CampaignRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/campaigns/${campaignId}/toggle-active`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": userId,
    },
    body: JSON.stringify({ is_active: isActive }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update campaign active status" }));
    throw new Error(err.detail || "Failed to update campaign active status");
  }
  return res.json();
}

export async function recordAdvertiserPayment(
  businessId: string,
  data: any,
  userId: string
): Promise<AdvertiserPaymentRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/businesses/${businessId}/payments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": userId,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Payment submission failed" }));
    throw new Error(err.detail || "Payment submission failed");
  }
  return res.json();
}

// --- Admin APIs ---

export async function getAdminRegistrations(
  adminToken: string,
  status?: string
): Promise<BusinessRegistrationRecord[]> {
  const url = new URL(`${API_BASE}/nammadeals/admin/registrations`);
  if (status) url.searchParams.set("status", status);

  const res = await fetch(url.toString(), {
    headers: { "X-Admin-Token": adminToken },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch registrations (Unauthorized or invalid admin token)");
  }
  return res.json();
}

export async function reviewRegistration(
  regId: string,
  action: "APPROVE" | "REJECT",
  adminToken: string,
  ownerUserId?: string,
  rejectionReason?: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/registrations/${regId}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": adminToken,
    },
    body: JSON.stringify({
      action,
      owner_user_id: ownerUserId,
      rejection_reason: rejectionReason,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Review action failed" }));
    throw new Error(err.detail || "Review action failed");
  }
  return res.json();
}

export async function getAdminCampaigns(
  adminToken: string,
  approvalStatus?: string
): Promise<CampaignRecord[]> {
  const url = new URL(`${API_BASE}/nammadeals/admin/campaigns`);
  if (approvalStatus) url.searchParams.set("approval_status", approvalStatus);

  const res = await fetch(url.toString(), {
    headers: { "X-Admin-Token": adminToken },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch campaigns for admin review");
  }
  return res.json();
}

export async function reviewCampaign(
  campaignId: string,
  action: "APPROVE" | "REJECT" | "SUSPEND",
  adminToken: string,
  rejectionReason?: string
): Promise<CampaignRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/campaigns/${campaignId}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": adminToken,
    },
    body: JSON.stringify({
      action,
      rejection_reason: rejectionReason,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Campaign review failed" }));
    throw new Error(err.detail || "Campaign review failed");
  }
  return res.json();
}

export async function updateBusinessStatus(
  businessId: string,
  status: "APPROVED" | "REJECTED" | "SUSPENDED",
  adminToken: string,
  reason?: string
): Promise<BusinessRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/businesses/${businessId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": adminToken,
    },
    body: JSON.stringify({ status, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update business status" }));
    throw new Error(err.detail || "Failed to update business status");
  }
  return res.json();
}

export async function getAdminBusinesses(
  adminToken: string,
  status?: string
): Promise<BusinessRecord[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await fetch(`${API_BASE}/nammadeals/admin/businesses${query}`, {
    headers: { "X-Admin-Token": adminToken },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch businesses" }));
    throw new Error(err.detail || "Failed to fetch businesses");
  }
  return res.json();
}

export interface AdminCampaignCreateData {
  business_id: string;
  name: string;
  description?: string;
  campaign_type?: "COUPON" | "SCRATCH_CARD";
  offer_title: string;
  offer_description?: string;
  discount_type?: "PERCENTAGE" | "FLAT" | "FREEBIE" | "REWARD";
  discount_value?: number;
  coupon_code: string;
  advertisement_image_url?: string;
  targeting_mode?: "PROFILE_ONLY" | "COMPLAINT_ONLY" | "BOTH";
  targeting_radius_km?: number;
  start_date: string;
  end_date: string;
  max_claims?: number;
  status?: "ACTIVE" | "DRAFT" | "PAUSED";
  terms_and_conditions?: string;
  scratch_card_config?: {
    win_headline?: string;
    description?: string;
    min_discount?: number;
    max_discount?: number;
  };
}

export async function uploadCampaignImage(
  file: File,
  adminToken: string
): Promise<{ success: boolean; image_key: string; image_url: string }> {
  const formData = new FormData();
  formData.append("image", file);

  const res = await fetch(`${API_BASE}/nammadeals/admin/campaigns/upload-image`, {
    method: "POST",
    headers: {
      "X-Admin-Token": adminToken,
    },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Image upload failed" }));
    throw new Error(err.detail || "Image upload failed");
  }
  return res.json();
}

export async function adminCreateCampaign(
  data: AdminCampaignCreateData,
  adminToken: string
): Promise<CampaignRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/campaigns`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": adminToken,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Campaign creation failed" }));
    throw new Error(err.detail || "Campaign creation failed");
  }
  return res.json();
}

export async function adminUpdateCampaign(
  campaignId: string,
  data: Partial<AdminCampaignCreateData>,
  adminToken: string
): Promise<CampaignRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/campaigns/${campaignId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": adminToken,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Campaign update failed" }));
    throw new Error(err.detail || "Campaign update failed");
  }
  return res.json();
}

export async function adminSetCampaignStatus(
  campaignId: string,
  status: "DRAFT" | "ACTIVE" | "PAUSED" | "EXPIRED" | "DEACTIVATED",
  adminToken: string
): Promise<CampaignRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/campaigns/${campaignId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": adminToken,
    },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update campaign status" }));
    throw new Error(err.detail || "Failed to update campaign status");
  }
  return res.json();
}

export async function adminUpdateBusinessLocation(
  businessId: string,
  data: {
    google_maps_url?: string;
    latitude?: number;
    longitude?: number;
    area?: string;
    address?: string;
  },
  adminToken: string
): Promise<BusinessRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/businesses/${businessId}/location`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": adminToken,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update business location" }));
    throw new Error(err.detail || "Failed to update business location");
  }
  return res.json();
}

export async function getAdminPayments(
  adminToken: string,
  status?: string
): Promise<AdvertiserPaymentRecord[]> {
  const url = new URL(`${API_BASE}/nammadeals/admin/payments`);
  if (status) url.searchParams.set("status", status);

  const res = await fetch(url.toString(), {
    headers: { "X-Admin-Token": adminToken },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch payments");
  }
  return res.json();
}

export async function verifyPayment(
  paymentId: string,
  action: "VERIFY" | "FAIL" | "REFUND",
  adminToken: string,
  adminNotes?: string
): Promise<AdvertiserPaymentRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/payments/${paymentId}/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": adminToken,
    },
    body: JSON.stringify({ action, admin_notes: adminNotes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Payment verification failed" }));
    throw new Error(err.detail || "Payment verification failed");
  }
  return res.json();
}

// ============================================================================
// Stage 4: Coupon Claims, Scratch Cards, In-Store Redemptions & Analytics
// ============================================================================

export interface CouponClaimRecord {
  id: string;
  citizen_user_id: string;
  campaign_id: string;
  offer_id: string;
  unique_coupon_code: string;
  status: "CLAIMED" | "REDEEMED" | "EXPIRED" | "CANCELLED";
  claimed_at: string;
  redeemed_at?: string | null;
  redeemed_by_business_id?: string | null;
  redemption_notes?: string | null;
  scratch_reward_revealed: boolean;
  claim_metadata?: any;
  business_id?: string | null;
  business_name?: string | null;
  business_area?: string | null;
  campaign_name?: string | null;
  offer_title?: string | null;
  offer_description?: string | null;
  offer_type?: "COUPON" | "SCRATCH_CARD" | "INSTANT_DISCOUNT" | null;
  discount_type?: "PERCENTAGE" | "FLAT" | "FREEBIE" | "REWARD" | null;
  discount_value?: number | null;
  terms_and_conditions?: string | null;
  valid_until?: string | null;
}

export interface ScratchCardRevealResult {
  success: boolean;
  message: string;
  claim: CouponClaimRecord;
  reward_headline: string;
  reward_description: string;
  discount_percentage?: number | null;
  revealed_at: string;
  is_already_revealed: boolean;
}

export interface CouponRedemptionResult {
  success: boolean;
  message: string;
  unique_coupon_code: string;
  redeemed_at: string;
  business_id: string;
  business_name: string;
  campaign_id: string;
  campaign_name: string;
  offer_id: string;
  offer_title: string;
  discount_summary: string;
  redemption_notes?: string | null;
  claim: CouponClaimRecord;
}

export interface CampaignAnalytics {
  campaign_id: string;
  campaign_name: string;
  status: string;
  impressions: number;
  clicks: number;
  claims: number;
  redemptions: number;
  ctr_percentage: number;
  claim_rate_percentage: number;
  redemption_rate_percentage: number;
  budget_allocated?: number | null;
}

export interface BusinessAnalytics {
  business_id: string;
  business_name: string;
  total_campaigns: number;
  active_campaigns: number;
  total_offers: number;
  impressions: number;
  clicks: number;
  claims: number;
  redemptions: number;
  overall_ctr_percentage: number;
  overall_redemption_rate_percentage: number;
  verified_payments_total: number;
}

export interface AdminPlatformAnalytics {
  total_registrations: number;
  pending_registrations: number;
  total_businesses: number;
  verified_businesses: number;
  total_campaigns: number;
  active_campaigns: number;
  pending_campaign_approvals: number;
  total_impressions: number;
  total_clicks: number;
  total_claims: number;
  total_redemptions: number;
  overall_ctr_percentage: number;
  total_revenue_inr: number;
  pending_revenue_inr: number;
}

export async function claimCoupon(
  offerId: string,
  citizenUserId: string,
  clientNotes?: string
): Promise<CouponClaimRecord> {
  const res = await fetch(`${API_BASE}/nammadeals/coupons/claim`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": citizenUserId,
    },
    body: JSON.stringify({
      offer_id: offerId,
      client_notes: clientNotes,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to claim coupon" }));
    throw new Error(err.detail || "Failed to claim coupon");
  }
  return res.json();
}

export async function getMyClaimedCoupons(
  citizenUserId: string,
  status?: string
): Promise<CouponClaimRecord[]> {
  const url = new URL(`${API_BASE}/nammadeals/coupons/my`);
  if (status) url.searchParams.set("status", status);

  const res = await fetch(url.toString(), {
    headers: { "X-User-ID": citizenUserId },
  });
  if (!res.ok) {
    throw new Error("Failed to load claimed coupons");
  }
  return res.json();
}

export async function revealScratchCard(
  offerId: string,
  citizenUserId: string
): Promise<ScratchCardRevealResult> {
  const res = await fetch(`${API_BASE}/nammadeals/scratch-cards/${offerId}/reveal`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": citizenUserId,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to reveal scratch card reward" }));
    throw new Error(err.detail || "Failed to reveal scratch card reward");
  }
  return res.json();
}

export async function redeemCouponInStore(
  businessId: string,
  ownerUserId: string,
  couponCode: string,
  notes?: string
): Promise<CouponRedemptionResult> {
  const res = await fetch(`${API_BASE}/nammadeals/businesses/${businessId}/redeem`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": ownerUserId,
    },
    body: JSON.stringify({
      coupon_code: couponCode,
      notes,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Redemption failed" }));
    throw new Error(err.detail || "Redemption failed");
  }
  return res.json();
}

export async function getCampaignAnalytics(
  campaignId: string,
  ownerUserId: string
): Promise<CampaignAnalytics> {
  const res = await fetch(`${API_BASE}/nammadeals/campaigns/${campaignId}/analytics`, {
    headers: { "X-User-ID": ownerUserId },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch campaign analytics");
  }
  return res.json();
}

export async function getBusinessAnalytics(
  businessId: string,
  ownerUserId: string
): Promise<BusinessAnalytics> {
  const res = await fetch(`${API_BASE}/nammadeals/businesses/${businessId}/analytics`, {
    headers: { "X-User-ID": ownerUserId },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch business analytics");
  }
  return res.json();
}

export async function getAdminPlatformAnalytics(
  adminToken: string
): Promise<AdminPlatformAnalytics> {
  const res = await fetch(`${API_BASE}/nammadeals/admin/analytics`, {
    headers: { "X-Admin-Token": adminToken },
  });
  if (!res.ok) {
    throw new Error("Failed to fetch platform analytics");
  }
  return res.json();
}

