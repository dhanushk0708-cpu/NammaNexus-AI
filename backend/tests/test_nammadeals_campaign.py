from datetime import datetime, timedelta, timezone
import pytest
from app.core.config import settings
from app.models.nammadeals import (
    Business,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    Offer,
    OfferType,
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
        latitude=12.9716,
        longitude=77.6412,
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz)
    session.commit()
    session.refresh(biz)
    return biz


def test_cannot_create_campaign_for_unapproved_business(test_client_and_db):
    client, session = test_client_and_db
    pending_biz = Business(
        owner_user_id=OWNER_ID,
        name="Pending Boutique",
        category="Fashion",
        email="pending@boutique.in",
        phone="9876543221",
        address="Brigade Rd",
        city="Bengaluru",
        area="MG Road",
        pincode="560001",
        status=BusinessStatus.PENDING.value,
    )
    session.add(pending_biz)
    session.commit()

    headers = {"X-User-ID": OWNER_ID}
    now = datetime.now(timezone.utc)
    payload = {
        "name": "Winter Promo",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=15)).isoformat(),
    }
    res = client.post(f"/api/v1/nammadeals/businesses/{pending_biz.id}/campaigns", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Only APPROVED businesses can create campaigns" in res.json()["detail"]


def test_create_campaign_draft(test_client_and_db, approved_business):
    client, _ = test_client_and_db
    headers = {"X-User-ID": OWNER_ID}
    now = datetime.now(timezone.utc)
    payload = {
        "name": "Morning Roast Special",
        "description": "20% off on all morning pour-overs.",
        "campaign_type": "DISCOUNT",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=10)).isoformat(),
        "targeting_strategy": "RADIUS",
        "targeting_radius_km": 4.5,
        "priority": 20,
        "frequency_limit_per_user": 2,
        "placement_config": {"placements": ["feed", "spotfix_confirmation"]},
    }

    res = client.post(f"/api/v1/nammadeals/businesses/{approved_business.id}/campaigns", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Morning Roast Special"
    assert data["approval_status"] == "DRAFT"
    assert data["is_active"] is False
    assert data["business_id"] == approved_business.id
    assert data["targeting_radius_km"] == 4.5


def test_campaign_offer_creation_and_validation(test_client_and_db, approved_business):
    client, _ = test_client_and_db
    headers = {"X-User-ID": OWNER_ID}
    now = datetime.now(timezone.utc)

    # 1. Create campaign
    camp_res = client.post(
        f"/api/v1/nammadeals/businesses/{approved_business.id}/campaigns",
        json={
            "name": "Festival Bonanza",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=30)).isoformat(),
        },
        headers=headers,
    )
    camp_id = camp_res.json()["id"]

    # 2. Coupon without coupon_code fails
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

    # 3. Valid coupon succeeds
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

    # 4. Scratch-card offer
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

    # 5. List offers for campaign
    res_list = client.get(f"/api/v1/nammadeals/campaigns/{camp_id}/offers", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 2


def test_campaign_approval_and_activation_lifecycle(test_client_and_db, approved_business):
    client, session = test_client_and_db
    headers = {"X-User-ID": OWNER_ID}
    admin_headers = {"X-Admin-Token": ADMIN_TOKEN}
    now = datetime.now(timezone.utc)

    # 1. Create campaign
    camp_res = client.post(
        f"/api/v1/nammadeals/businesses/{approved_business.id}/campaigns",
        json={
            "name": "Weekend Monsoon Special",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=10)).isoformat(),
        },
        headers=headers,
    )
    camp_id = camp_res.json()["id"]

    # 2. Cannot submit without offer
    sub_fail = client.post(f"/api/v1/nammadeals/campaigns/{camp_id}/submit-approval", headers=headers)
    assert sub_fail.status_code == 400
    assert "without at least one promotional offer" in sub_fail.json()["detail"]

    # 3. Add offer
    client.post(
        f"/api/v1/nammadeals/campaigns/{camp_id}/offers",
        json={
            "title": "Buy 1 Get 1 Free Cold Brew",
            "discount_type": "FREEBIE",
            "discount_value": 100.0,
            "valid_from": now.isoformat(),
            "valid_until": (now + timedelta(days=10)).isoformat(),
            "offer_type": "COUPON",
            "coupon_code": "COLDBREW100",
        },
        headers=headers,
    )

    # 4. Now submit succeeds -> PENDING_APPROVAL
    sub_ok = client.post(f"/api/v1/nammadeals/campaigns/{camp_id}/submit-approval", headers=headers)
    assert sub_ok.status_code == 200
    assert sub_ok.json()["approval_status"] == "PENDING_APPROVAL"

    # 5. Advertiser cannot activate campaign while PENDING_APPROVAL
    act_fail = client.post(
        f"/api/v1/nammadeals/campaigns/{camp_id}/toggle-active",
        json={"is_active": True},
        headers=headers,
    )
    assert act_fail.status_code == 400
    assert "Only APPROVED campaigns can be activated" in act_fail.json()["detail"]

    # 6. Admin approves campaign
    admin_rev = client.post(
        f"/api/v1/nammadeals/admin/campaigns/{camp_id}/review",
        json={"action": "APPROVE"},
        headers=admin_headers,
    )
    assert admin_rev.status_code == 200
    assert admin_rev.json()["approval_status"] == "APPROVED"

    # 7. Now advertiser can activate campaign
    act_ok = client.post(
        f"/api/v1/nammadeals/campaigns/{camp_id}/toggle-active",
        json={"is_active": True},
        headers=headers,
    )
    assert act_ok.status_code == 200
    assert act_ok.json()["is_active"] is True
