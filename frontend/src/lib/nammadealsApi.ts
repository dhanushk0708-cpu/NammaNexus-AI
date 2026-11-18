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
  matched_location_source: "COMPLAINT" | "PROFILE" | "NEARBY" | "CITYWIDE" | "ONLINE";
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
  latitude?: number;
  longitude?: number;
}

export interface BusinessRegistrationRecord extends BusinessRegistrationData {
  id: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
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
