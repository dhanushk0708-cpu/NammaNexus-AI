from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from app.core.config import settings
from app.models.nammadeals import (
    AdvertiserPayment,
    Business,
    BusinessRegistration,
    BusinessRegistrationStatus,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    CampaignType,
    CouponClaim,
    CouponClaimStatus,
    DiscountType,
    Offer,
    OfferType,
    PaymentMethod,
    PaymentVerificationStatus,
    PromotionEvent,
    PromotionEventType,
    TargetingStrategy,
)

ADMIN_TOKEN = "test-nammadeals-admin-secret-token"


@pytest.fixture(autouse=True)
def configure_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "nammadeals_admin_token", ADMIN_TOKEN)


def _create_test_business_and_campaign(session, owner_id="biz_owner_1", biz_name="Bengaluru Cafe"):
    now = datetime.now(timezone.utc)
    biz = Business(
        id=str(uuid4()),
        owner_user_id=owner_id,
        name=biz_name,
        category="Food & Beverage",
        email=f"{owner_id}@test.com",
        phone="+919876543210",
        address="100 Indiranagar 100ft Road",
        city="Bengaluru",
        area="Indiranagar",
        pincode="560038",
        latitude=12.9784,
        longitude=77.6408,
        status=BusinessStatus.APPROVED.value,
        created_at=now,
        updated_at=now,
    )
    session.add(biz)

    camp = Campaign(
        id=str(uuid4()),
        business_id=biz.id,
        name="Indiranagar Monsoon Offer",
        campaign_type=CampaignType.COUPON.value,
        targeting_strategy=TargetingStrategy.RADIUS.value,
        targeting_radius_km=5.0,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=10),
        is_active=True,
        approval_status=CampaignApprovalStatus.APPROVED.value,
        priority=10,
        frequency_limit_per_user=5,
        created_at=now,
        updated_at=now,
    )
    session.add(camp)

    # Standard coupon offer
    standard_offer = Offer(
        id=str(uuid4()),
        campaign_id=camp.id,
        title="20% Off Filter Coffee",
        description="Get 20% off handcrafted South Indian filter coffee and breakfast combos.",
        discount_type=DiscountType.PERCENTAGE.value,
        discount_value=20.0,
        terms_and_conditions="Valid for dine-in orders only.",
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=5),
        offer_type=OfferType.COUPON.value,
        coupon_code="FILTER20",
        max_redemptions=100,
        redemption_count=0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(standard_offer)

    # Predetermined scratch-card offer
    scratch_offer = Offer(
        id=str(uuid4()),
        campaign_id=camp.id,
        title="Mystery Monsoon Delight",
        description="Scratch to reveal an exclusive café discount.",
        discount_type=DiscountType.PERCENTAGE.value,
        discount_value=30.0,
        terms_and_conditions="Must show code to billing staff before bill generation.",
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=5),
        offer_type=OfferType.SCRATCH_CARD.value,
        coupon_code="SCRATCH30",
        scratch_card_config={
            "win_headline": "30% Off All Hot Beverages",
            "description": "Predetermined 30% discount on artisan coffee and artisanal snacks.",
            "min_discount": 30.0,
            "max_discount": 30.0,
        },
        max_redemptions=50,
        redemption_count=0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(scratch_offer)
    session.commit()

    return biz, camp, standard_offer, scratch_offer


# ============================================================================
# 1. Coupon Claim Tests
# ============================================================================

def test_claim_standard_coupon_success(test_client_and_db):
    client, session = test_client_and_db
    biz, camp, standard_offer, _ = _create_test_business_and_campaign(session)

    citizen_id = "citizen_aadhaar_001"
    response = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": citizen_id},
        json={"offer_id": standard_offer.id, "client_notes": "Claimed from SpotFix confirmation"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["citizen_user_id"] == citizen_id
    assert data["offer_id"] == standard_offer.id
    assert data["campaign_id"] == camp.id
    assert data["status"] == "CLAIMED"
    assert data["unique_coupon_code"].startswith("FILTER20-")
    assert data["business_name"] == "Bengaluru Cafe"
    assert data["offer_title"] == "20% Off Filter Coffee"

    # Verify database persistence
    claim = session.query(CouponClaim).filter(CouponClaim.unique_coupon_code == data["unique_coupon_code"]).first()
    assert claim is not None
    assert claim.citizen_user_id == citizen_id
    assert claim.status == CouponClaimStatus.CLAIMED.value

    # Verify CLAIM event logged
    event = (
        session.query(PromotionEvent)
        .filter(
            PromotionEvent.event_type == PromotionEventType.CLAIM.value,
            PromotionEvent.citizen_user_id == citizen_id,
        )
        .first()
    )
    assert event is not None
    assert event.campaign_id == camp.id
    assert event.offer_id == standard_offer.id


def test_claim_coupon_idempotent_duplicate_prevention(test_client_and_db):
    client, session = test_client_and_db
    _, _, standard_offer, _ = _create_test_business_and_campaign(session)
    citizen_id = "citizen_aadhaar_002"

    # First claim
    res1 = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": citizen_id},
        json={"offer_id": standard_offer.id},
    )
    assert res1.status_code == 201
    code1 = res1.json()["unique_coupon_code"]

    # Second claim attempt for identical offer by same citizen
    res2 = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": citizen_id},
        json={"offer_id": standard_offer.id},
    )
    # Should safely return the existing claim without creating duplicate code or 500 error
    assert res2.status_code == 201
    assert res2.json()["unique_coupon_code"] == code1

    # Verify exactly 1 claim in database
    claim_count = session.query(CouponClaim).filter(
        CouponClaim.citizen_user_id == citizen_id,
        CouponClaim.offer_id == standard_offer.id,
    ).count()
    assert claim_count == 1


def test_claim_expired_or_inactive_offer_rejected(test_client_and_db):
    client, session = test_client_and_db
    _, _, standard_offer, _ = _create_test_business_and_campaign(session)

    # Inactivate offer
    standard_offer.is_active = False
    session.commit()

    res = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": "citizen_003"},
        json={"offer_id": standard_offer.id},
    )
    assert res.status_code == 400
    assert "inactive" in res.json()["detail"].lower()


def test_list_my_claimed_coupons(test_client_and_db):
    client, session = test_client_and_db
    _, _, standard_offer, scratch_offer = _create_test_business_and_campaign(session)
    citizen_id = "citizen_004"

    # Claim standard offer
    client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": citizen_id},
        json={"offer_id": standard_offer.id},
    )
    # Claim scratch offer
    client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": citizen_id},
        json={"offer_id": scratch_offer.id},
    )

    # Retrieve all claimed coupons
    res = client.get(
        "/api/v1/nammadeals/coupons/my",
        headers={"X-User-ID": citizen_id},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    codes = {item["unique_coupon_code"] for item in items}
    assert len(codes) == 2


# ============================================================================
# 2. Predetermined Scratch-Card Tests
# ============================================================================

def test_scratch_card_reveal_predetermined_consistency(test_client_and_db):
    client, session = test_client_and_db
    _, _, _, scratch_offer = _create_test_business_and_campaign(session)
    citizen_id = "citizen_005"

    # Reveal scratch card
    res1 = client.post(
        f"/api/v1/nammadeals/scratch-cards/{scratch_offer.id}/reveal",
        headers={"X-User-ID": citizen_id},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["is_already_revealed"] is False
    assert data1["reward_headline"] == "30% Off All Hot Beverages"
    assert data1["discount_percentage"] == 30.0

    # Repeat reveal call must return the exact same persisted reward (no random lottery)
    res2 = client.post(
        f"/api/v1/nammadeals/scratch-cards/{scratch_offer.id}/reveal",
        headers={"X-User-ID": citizen_id},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_already_revealed"] is True
    assert data2["reward_headline"] == data1["reward_headline"]
    assert data2["discount_percentage"] == data1["discount_percentage"]
    assert data2["claim"]["unique_coupon_code"] == data1["claim"]["unique_coupon_code"]


def test_scratch_card_reveal_rejected_for_standard_coupon(test_client_and_db):
    client, session = test_client_and_db
    _, _, standard_offer, _ = _create_test_business_and_campaign(session)
    citizen_id = "citizen_006"

    # Standard coupon cannot be revealed as a scratch card
    res = client.post(
        f"/api/v1/nammadeals/scratch-cards/{standard_offer.id}/reveal",
        headers={"X-User-ID": citizen_id},
    )
    assert res.status_code == 400
    assert "not a scratch card" in res.json()["detail"].lower()


# ============================================================================
# 3. Merchant In-Store Coupon Redemption Tests
# ============================================================================

def test_merchant_redeem_coupon_success(test_client_and_db):
    client, session = test_client_and_db
    biz, camp, standard_offer, _ = _create_test_business_and_campaign(session, owner_id="cafe_owner_1")
    citizen_id = "citizen_007"

    # Citizen claims coupon
    claim_res = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": citizen_id},
        json={"offer_id": standard_offer.id},
    )
    coupon_code = claim_res.json()["unique_coupon_code"]

    # Merchant redeems coupon in-store
    redeem_res = client.post(
        f"/api/v1/nammadeals/businesses/{biz.id}/redeem",
        headers={"X-User-ID": "cafe_owner_1"},
        json={"coupon_code": coupon_code, "notes": "Order #4092 - Dine in"},
    )
    assert redeem_res.status_code == 200
    r_data = redeem_res.json()
    assert r_data["success"] is True
    assert r_data["unique_coupon_code"] == coupon_code
    assert r_data["business_id"] == biz.id
    assert r_data["business_name"] == biz.name
    assert "20% OFF" in r_data["discount_summary"]

    # Verify DB update
    claim = session.query(CouponClaim).filter(CouponClaim.unique_coupon_code == coupon_code).first()
    assert claim.status == CouponClaimStatus.REDEEMED.value
    assert claim.redeemed_at is not None
    assert claim.redeemed_by_business_id == biz.id

    # Verify offer redemption count incremented
    session.refresh(standard_offer)
    assert standard_offer.redemption_count == 1

    # Verify REDEMPTION event logged
    event = (
        session.query(PromotionEvent)
        .filter(
            PromotionEvent.event_type == PromotionEventType.REDEMPTION.value,
            PromotionEvent.campaign_id == camp.id,
        )
        .first()
    )
    assert event is not None


def test_merchant_redeem_double_redemption_prevention(test_client_and_db):
    client, session = test_client_and_db
    biz, _, standard_offer, _ = _create_test_business_and_campaign(session, owner_id="cafe_owner_2")
    citizen_id = "citizen_008"

    claim_res = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": citizen_id},
        json={"offer_id": standard_offer.id},
    )
    coupon_code = claim_res.json()["unique_coupon_code"]

    # First redemption succeeds
    r1 = client.post(
        f"/api/v1/nammadeals/businesses/{biz.id}/redeem",
        headers={"X-User-ID": "cafe_owner_2"},
        json={"coupon_code": coupon_code},
    )
    assert r1.status_code == 200

    # Second redemption attempt MUST be rejected
    r2 = client.post(
        f"/api/v1/nammadeals/businesses/{biz.id}/redeem",
        headers={"X-User-ID": "cafe_owner_2"},
        json={"coupon_code": coupon_code},
    )
    assert r2.status_code == 400
    assert "already been redeemed" in r2.json()["detail"].lower()


def test_merchant_cross_business_redemption_rejected(test_client_and_db):
    client, session = test_client_and_db
    biz_a, _, offer_a, _ = _create_test_business_and_campaign(session, owner_id="owner_a", biz_name="Business A")
    biz_b, _, _, _ = _create_test_business_and_campaign(session, owner_id="owner_b", biz_name="Business B")

    # Citizen claims coupon for Business A
    claim_res = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": "citizen_009"},
        json={"offer_id": offer_a.id},
    )
    coupon_code = claim_res.json()["unique_coupon_code"]

    # Business B attempts to redeem Business A's coupon
    res = client.post(
        f"/api/v1/nammadeals/businesses/{biz_b.id}/redeem",
        headers={"X-User-ID": "owner_b"},
        json={"coupon_code": coupon_code},
    )
    assert res.status_code == 403
    assert "not for your business" in res.json()["detail"].lower()


def test_merchant_unauthorized_user_redemption_rejected(test_client_and_db):
    client, session = test_client_and_db
    biz, _, standard_offer, _ = _create_test_business_and_campaign(session, owner_id="legit_owner")

    claim_res = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": "citizen_010"},
        json={"offer_id": standard_offer.id},
    )
    coupon_code = claim_res.json()["unique_coupon_code"]

    # Random attacker tries to redeem on behalf of business
    res = client.post(
        f"/api/v1/nammadeals/businesses/{biz.id}/redeem",
        headers={"X-User-ID": "random_attacker"},
        json={"coupon_code": coupon_code},
    )
    assert res.status_code == 403


# ============================================================================
# 4. Analytics & Intelligence Tests
# ============================================================================

def test_campaign_and_business_analytics(test_client_and_db):
    client, session = test_client_and_db
    biz, camp, standard_offer, _ = _create_test_business_and_campaign(session, owner_id="analytics_owner")

    # Seed impressions and clicks
    now = datetime.now(timezone.utc)
    for _ in range(10):
        session.add(
            PromotionEvent(
                id=str(uuid4()),
                event_type=PromotionEventType.IMPRESSION.value,
                campaign_id=camp.id,
                offer_id=standard_offer.id,
                citizen_user_id="cit_test",
                created_at=now,
            )
        )
    for _ in range(2):
        session.add(
            PromotionEvent(
                id=str(uuid4()),
                event_type=PromotionEventType.CLICK.value,
                campaign_id=camp.id,
                offer_id=standard_offer.id,
                citizen_user_id="cit_test",
                created_at=now,
            )
        )
    session.commit()

    # Claim and redeem
    claim_res = client.post(
        "/api/v1/nammadeals/coupons/claim",
        headers={"X-User-ID": "cit_test"},
        json={"offer_id": standard_offer.id},
    )
    code = claim_res.json()["unique_coupon_code"]

    client.post(
        f"/api/v1/nammadeals/businesses/{biz.id}/redeem",
        headers={"X-User-ID": "analytics_owner"},
        json={"coupon_code": code},
    )

    # 1. Fetch Campaign Analytics
    c_res = client.get(
        f"/api/v1/nammadeals/campaigns/{camp.id}/analytics",
        headers={"X-User-ID": "analytics_owner"},
    )
    assert c_res.status_code == 200
    c_data = c_res.json()
    assert c_data["impressions"] == 10
    assert c_data["clicks"] == 2
    assert c_data["claims"] == 1
    assert c_data["redemptions"] == 1
    assert c_data["ctr_percentage"] == 20.0
    assert c_data["redemption_rate_percentage"] == 100.0

    # 2. Fetch Business Analytics
    b_res = client.get(
        f"/api/v1/nammadeals/businesses/{biz.id}/analytics",
        headers={"X-User-ID": "analytics_owner"},
    )
    assert b_res.status_code == 200
    b_data = b_res.json()
    assert b_data["business_name"] == "Bengaluru Cafe"
    assert b_data["impressions"] == 10
    assert b_data["clicks"] == 2
    assert b_data["claims"] == 1
    assert b_data["redemptions"] == 1


def test_admin_platform_analytics(test_client_and_db):
    client, session = test_client_and_db
    biz, camp, _, _ = _create_test_business_and_campaign(session)

    # Add a verified payment
    now = datetime.now(timezone.utc)
    payment = AdvertiserPayment(
        id=str(uuid4()),
        business_id=biz.id,
        campaign_id=camp.id,
        amount=2500.0,
        currency="INR",
        transaction_id="TXN_ADMIN_VERIFIED_123",
        payment_method=PaymentMethod.UPI.value,
        payment_date=now,
        verification_status=PaymentVerificationStatus.VERIFIED.value,
        created_at=now,
        updated_at=now,
    )
    session.add(payment)
    session.commit()

    res = client.get(
        "/api/v1/nammadeals/admin/analytics",
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert res.status_code == 200
    admin_data = res.json()
    assert admin_data["total_businesses"] >= 1
    assert admin_data["verified_businesses"] >= 1
    assert admin_data["total_campaigns"] >= 1
    assert admin_data["total_revenue_inr"] == 2500.0
