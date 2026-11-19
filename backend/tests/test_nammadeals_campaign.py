from datetime import datetime, timedelta, timezone
import io
import pytest
from PIL import Image

from app.core.config import settings
from app.models.nammadeals import (
    Business,
    BusinessRegistration,
    BusinessRegistrationStatus,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    CampaignStatus,
    Offer,
    OfferType,
    TargetingMode,
)


ADMIN_TOKEN = "test-nammadeals-admin-secret-token"
OWNER_ID = "usr_campaign_owner_1"


@pytest.fixture(autouse=True)
def configure_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "nammadeals_admin_token", ADMIN_TOKEN)


@pytest.fixture
def approved_business(test_client_and_db):
    _, session = test_client_and_db
    biz = Business(
        owner_user_id=OWNER_ID,
        name="Artisan Coffee Roasters",
        category="Cafe",
        email="artisan@coffee.in",
        phone="9876543220",
        address="12th Main, HAL 2nd Stage, Indiranagar",
        city="Bengaluru",
        area="Indiranagar",
        pincode="560038",
        google_maps_url="https://maps.app.goo.gl/artisanIndiranagar",
        latitude=12.9716,
        longitude=77.6412,
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz)
    session.commit()
    session.refresh(biz)
    return biz


def test_merchant_cannot_create_campaign(test_client_and_db, approved_business):
    """Enforces critical business rule: Only admins can create campaigns; merchants receive HTTP 403."""
    client, _ = test_client_and_db
    headers = {"X-User-ID": OWNER_ID}
    now = datetime.now(timezone.utc)
    payload = {
        "name": "Unauthorized Merchant Campaign",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=15)).isoformat(),
    }
    res = client.post(
        f"/api/v1/nammadeals/businesses/{approved_business.id}/campaigns",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 403
    assert "Only platform administrators can create or publish campaigns" in res.json()["detail"]


def test_admin_create_campaign_success(test_client_and_db, approved_business):
    """Admin creates a complete campaign with offer, banner, and targeting."""
    client, _ = test_client_and_db
    admin_headers = {"X-Admin-Token": ADMIN_TOKEN}
    now = datetime.now(timezone.utc)
    payload = {
        "business_id": approved_business.id,
        "name": "Artisan Cold Brew Delight",
        "description": "Premium nitro cold brews for Indiranagar residents.",
        "campaign_type": "COUPON",
        "offer_title": "Flat 25% Off Cold Brews",
        "offer_description": "Valid on all large nitro cold brew variants.",
        "discount_type": "PERCENTAGE",
        "discount_value": 25.0,
        "coupon_code": "COLD25",
        "advertisement_image_url": "/api/v1/nammadeals/images/cold_brew_banner.jpg",
        "targeting_mode": "BOTH",
        "targeting_radius_km": 3.5,
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=14)).isoformat(),
        "max_claims": 200,
        "status": "ACTIVE",
    }
    res = client.post("/api/v1/nammadeals/admin/campaigns", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Artisan Cold Brew Delight"
    assert data["status"] == "ACTIVE"
    assert data["is_active"] is True
    assert data["advertisement_image_url"] == "/api/v1/nammadeals/images/cold_brew_banner.jpg"
    assert data["targeting_mode"] == "BOTH"
    assert data["business_name"] == "Artisan Coffee Roasters"
    assert data["business_area"] == "Indiranagar"
    assert data["store_maps_url"] == "https://maps.app.goo.gl/artisanIndiranagar"
    assert data["offers_count"] == 1
    assert data["max_claims"] == 200


def test_admin_update_campaign(test_client_and_db, approved_business):
    """Admin updates campaign targeting, schedule, and banner image."""
    client, session = test_client_and_db
    admin_headers = {"X-Admin-Token": ADMIN_TOKEN}
    now = datetime.now(timezone.utc)

    # 1. Create campaign via admin
    create_payload = {
        "business_id": approved_business.id,
        "name": "Morning Brew Promo",
        "campaign_type": "COUPON",
        "offer_title": "20% Off",
        "coupon_code": "BREW20",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=7)).isoformat(),
    }
    c_res = client.post("/api/v1/nammadeals/admin/campaigns", json=create_payload, headers=admin_headers)
    camp_id = c_res.json()["id"]

    # 2. Update campaign
    update_payload = {
        "name": "Updated Morning Pour-over",
        "advertisement_image_url": "/api/v1/nammadeals/images/new_banner.png",
        "targeting_mode": "COMPLAINT_ONLY",
        "targeting_radius_km": 5.0,
        "discount_value": 30.0,
    }
    u_res = client.put(f"/api/v1/nammadeals/admin/campaigns/{camp_id}", json=update_payload, headers=admin_headers)
    assert u_res.status_code == 200
    u_data = u_res.json()
    assert u_data["name"] == "Updated Morning Pour-over"
    assert u_data["advertisement_image_url"] == "/api/v1/nammadeals/images/new_banner.png"
    assert u_data["targeting_mode"] == "COMPLAINT_ONLY"
    assert u_data["targeting_radius_km"] == 5.0


def test_admin_set_campaign_status(test_client_and_db, approved_business):
    """Admin pauses, activates, and deactivates a campaign."""
    client, _ = test_client_and_db
    admin_headers = {"X-Admin-Token": ADMIN_TOKEN}
    now = datetime.now(timezone.utc)

    c_res = client.post(
        "/api/v1/nammadeals/admin/campaigns",
        json={
            "business_id": approved_business.id,
            "name": "Status Cycle Test",
            "campaign_type": "COUPON",
            "offer_title": "15% Off",
            "coupon_code": "CYCLE15",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=5)).isoformat(),
            "status": "ACTIVE",
        },
        headers=admin_headers,
    )
    camp_id = c_res.json()["id"]
    assert c_res.json()["status"] == "ACTIVE"
    assert c_res.json()["is_active"] is True

    # Pause campaign
    pause_res = client.patch(
        f"/api/v1/nammadeals/admin/campaigns/{camp_id}/status",
        json={"status": "PAUSED"},
        headers=admin_headers,
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"
    assert pause_res.json()["is_active"] is False

    # Reactivate campaign
    act_res = client.patch(
        f"/api/v1/nammadeals/admin/campaigns/{camp_id}/status",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert act_res.status_code == 200
    assert act_res.json()["status"] == "ACTIVE"
    assert act_res.json()["is_active"] is True


def test_admin_upload_and_serve_image(test_client_and_db):
    """Admin uploads a promotional banner and serves it publicly."""
    client, _ = test_client_and_db
    admin_headers = {"X-Admin-Token": ADMIN_TOKEN}

    # Generate synthetic JPEG in-memory
    buf = io.BytesIO()
    img = Image.new("RGB", (300, 200), color=(50, 120, 220))
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"image": ("ad_banner.jpg", buf.getvalue(), "image/jpeg")}
    upload_res = client.post(
        "/api/v1/nammadeals/admin/campaigns/upload-image",
        files=files,
        headers=admin_headers,
    )
    assert upload_res.status_code == 200
    up_data = upload_res.json()
    assert up_data["success"] is True
    assert "image_key" in up_data
    assert "image_url" in up_data

    # Fetch uploaded image publicly
    image_key = up_data["image_key"]
    get_res = client.get(f"/api/v1/nammadeals/images/{image_key}")
    assert get_res.status_code == 200
    assert len(get_res.content) == len(buf.getvalue())


def test_admin_update_business_location(test_client_and_db, approved_business):
    """Admin verifies and edits business location and Google Maps link."""
    client, _ = test_client_and_db
    admin_headers = {"X-Admin-Token": ADMIN_TOKEN}

    update_payload = {
        "google_maps_url": "https://maps.google.com/?q=12.9750,77.6450",
        "area": "Indiranagar Stage 2",
    }
    res = client.patch(
        f"/api/v1/nammadeals/admin/businesses/{approved_business.id}/location",
        json=update_payload,
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["area"] == "Indiranagar Stage 2"
    assert data["latitude"] == 12.9750
    assert data["longitude"] == 77.6450
    assert "maps.google.com" in data["google_maps_store_url"]


def test_campaign_offer_creation_and_validation(test_client_and_db, approved_business):
    """Offers added to existing campaigns validate types, percentages, and scratch configs."""
    client, session = test_client_and_db
    headers = {"X-User-ID": OWNER_ID}
    now = datetime.now(timezone.utc)

    # Create campaign directly
    camp = Campaign(
        business_id=approved_business.id,
        name="Festival Bonanza",
        campaign_type="DISCOUNT",
        start_date=now,
        end_date=now + timedelta(days=30),
        approval_status="DRAFT",
        is_active=False,
        targeting_strategy="RADIUS",
        targeting_radius_km=3.0,
        priority=10,
        frequency_limit_per_user=3,
    )
    session.add(camp)
    session.commit()
    camp_id = camp.id

    # 1. Coupon without coupon_code fails
    bad_coupon = {
        "title": "Flat 25% Off",
        "discount_type": "PERCENTAGE",
        "discount_value": 25.0,
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=15)).isoformat(),
        "offer_type": "COUPON",
    }
    res = client.post(f"/api/v1/nammadeals/campaigns/{camp_id}/offers", json=bad_coupon, headers=headers)
    assert res.status_code == 422

    # 2. Valid coupon succeeds
    valid_coupon = {
        "title": "Flat 25% Off",
        "discount_type": "PERCENTAGE",
        "discount_value": 25.0,
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=15)).isoformat(),
        "offer_type": "COUPON",
        "coupon_code": "NAMMA25",
        "max_redemptions": 50,
    }
    res = client.post(f"/api/v1/nammadeals/campaigns/{camp_id}/offers", json=valid_coupon, headers=headers)
    assert res.status_code == 201
    offer_data = res.json()
    assert offer_data["coupon_code"] == "NAMMA25"
    assert offer_data["is_active"] is True

    # 3. Scratch-card offer
    scratch_card = {
        "title": "Mystery Coffee Scratch Card",
        "discount_type": "REWARD",
        "discount_value": 50.0,
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=15)).isoformat(),
        "offer_type": "SCRATCH_CARD",
        "scratch_card_config": {
            "win_headline": "Win up to 50% discount",
            "min_discount": 10,
            "max_discount": 50,
        },
        "max_redemptions": 100,
    }
    res_scratch = client.post(f"/api/v1/nammadeals/campaigns/{camp_id}/offers", json=scratch_card, headers=headers)
    assert res_scratch.status_code == 201
    assert res_scratch.json()["offer_type"] == "SCRATCH_CARD"


def test_admin_create_campaign_resolves_via_registration_id(test_client_and_db):
    """Test creating campaign by passing registration_id instead of business_id gracefully resolves to Business."""
    client, session = test_client_and_db
    reg = BusinessRegistration(
        business_name="Test Silk Hub",
        category="Fashion",
        contact_name="Vinay",
        email="vinay@silkhub.in",
        phone="9876543291",
        address="Commercial Street",
        city="Bengaluru",
        area="Commercial Street",
        pincode="560001",
        status=BusinessRegistrationStatus.APPROVED.value,
    )
    session.add(reg)
    session.commit()

    # Create corresponding business
    biz = Business(
        owner_user_id="usr_vinay",
        registration_id=reg.id,
        name="Test Silk Hub",
        category="Fashion",
        email="vinay@silkhub.in",
        phone="9876543291",
        address="Commercial Street",
        city="Bengaluru",
        area="Commercial Street",
        pincode="560001",
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz)
    session.commit()

    headers = {"X-Admin-Token": ADMIN_TOKEN}
    now = datetime.now(timezone.utc)
    # Pass reg.id as business_id in payload
    payload = {
        "business_id": reg.id,
        "name": "Silk Sarees Festive Sale",
        "offer_title": "Flat 30% Off",
        "coupon_code": "SILK30",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=10)).isoformat(),
        "targeting_radius_km": 5.0,
    }
    res = client.post("/api/v1/nammadeals/admin/campaigns", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["business_id"] == biz.id
    assert data["name"] == "Silk Sarees Festive Sale"

