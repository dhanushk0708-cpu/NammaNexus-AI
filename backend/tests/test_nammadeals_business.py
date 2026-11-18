from datetime import datetime, timezone
import pytest
from app.core.config import settings
from app.models.nammadeals import (
    Business,
    BusinessRegistration,
    BusinessRegistrationStatus,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
)


ADMIN_TOKEN = "test-nammadeals-admin-secret-token"


@pytest.fixture(autouse=True)
def configure_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "nammadeals_admin_token", ADMIN_TOKEN)


# ============================================================================
# 1. Business Registration Tests
# ============================================================================

def test_submit_business_registration_success(test_client_and_db):
    client, session = test_client_and_db

    payload = {
        "business_name": "Corner House Ice Cream",
        "description": "Famous handcrafted sundaes and desserts.",
        "category": "Food & Beverage",
        "contact_name": "Narayan Rao",
        "email": "narayan@cornerhouse.in",
        "phone": "+91 9876543210",
        "address": "123, 7th Block, Koramangala",
        "city": "Bengaluru",
        "area": "Koramangala",
        "pincode": "560095",
        "latitude": 12.9352,
        "longitude": 77.6245,
    }

    response = client.post("/api/v1/nammadeals/registrations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["business_name"] == "Corner House Ice Cream"
    assert data["status"] == "PENDING"
    assert data["area"] == "Koramangala"
    assert data["pincode"] == "560095"

    # Verify in DB
    reg = session.query(BusinessRegistration).filter(BusinessRegistration.id == data["id"]).first()
    assert reg is not None
    assert reg.status == BusinessRegistrationStatus.PENDING.value


def test_submit_business_registration_invalid_inputs(test_client_and_db):
    client, _ = test_client_and_db

    # Invalid phone (too short)
    payload_bad_phone = {
        "business_name": "Quick Snacks",
        "category": "Food",
        "contact_name": "Ravi",
        "email": "ravi@snacks.in",
        "phone": "12345",
        "address": "Indiranagar 100ft road",
        "area": "Indiranagar",
        "pincode": "560038",
    }
    res = client.post("/api/v1/nammadeals/registrations", json=payload_bad_phone)
    assert res.status_code == 422

    # Invalid pincode (not 6 digits)
    payload_bad_pincode = {
        "business_name": "Quick Snacks",
        "category": "Food",
        "contact_name": "Ravi",
        "email": "ravi@snacks.in",
        "phone": "9876543210",
        "address": "Indiranagar 100ft road",
        "area": "Indiranagar",
        "pincode": "56003",
    }
    res = client.post("/api/v1/nammadeals/registrations", json=payload_bad_pincode)
    assert res.status_code == 422


def test_admin_list_and_get_registrations(test_client_and_db):
    client, session = test_client_and_db

    reg = BusinessRegistration(
        business_name="Indiranagar Chai Point",
        category="Cafe",
        contact_name="Amrit",
        email="amrit@chaipoint.com",
        phone="9876543211",
        address="100 Feet Rd",
        city="Bengaluru",
        area="Indiranagar",
        pincode="560038",
        status=BusinessRegistrationStatus.PENDING.value,
    )
    session.add(reg)
    session.commit()

    headers = {"X-Admin-Token": ADMIN_TOKEN}
    res = client.get("/api/v1/nammadeals/admin/registrations", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert items[0]["business_name"] == "Indiranagar Chai Point"

    # Get single registration
    res_single = client.get(f"/api/v1/nammadeals/admin/registrations/{reg.id}", headers=headers)
    assert res_single.status_code == 200
    assert res_single.json()["id"] == reg.id


def test_admin_approve_registration_creates_business(test_client_and_db):
    client, session = test_client_and_db

    reg = BusinessRegistration(
        business_name="CTR Vidyarthi Bhavan",
        category="Restaurant",
        contact_name="Sanjiv Rao",
        email="sanjiv@ctr.in",
        phone="9876543212",
        address="Margosa Road, Malleshwaram",
        city="Bengaluru",
        area="Malleshwaram",
        pincode="560003",
        status=BusinessRegistrationStatus.PENDING.value,
    )
    session.add(reg)
    session.commit()

    headers = {"X-Admin-Token": ADMIN_TOKEN}
    payload = {
        "action": "APPROVE",
        "owner_user_id": "usr_sanjiv_123",
    }
    res = client.post(f"/api/v1/nammadeals/admin/registrations/{reg.id}/review", json=payload, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["registration"]["status"] == "APPROVED"
    assert body["business"] is not None
    assert body["business"]["owner_user_id"] == "usr_sanjiv_123"
    assert body["business"]["name"] == "CTR Vidyarthi Bhavan"
    assert body["business"]["status"] == "APPROVED"

    # Verify database state
    db_business = session.query(Business).filter(Business.registration_id == reg.id).first()
    assert db_business is not None
    assert db_business.status == BusinessStatus.APPROVED.value


def test_admin_reject_registration_with_reason(test_client_and_db):
    client, session = test_client_and_db

    reg = BusinessRegistration(
        business_name="Fake Spa & Wellness",
        category="Spa",
        contact_name="Scammer",
        email="scam@notreal.in",
        phone="9876543213",
        address="Unknown address",
        city="Bengaluru",
        area="Whitefield",
        pincode="560066",
        status=BusinessRegistrationStatus.PENDING.value,
    )
    session.add(reg)
    session.commit()

    headers = {"X-Admin-Token": ADMIN_TOKEN}
    payload = {
        "action": "REJECT",
        "rejection_reason": "Incomplete documentation and unverifiable business location.",
    }
    res = client.post(f"/api/v1/nammadeals/admin/registrations/{reg.id}/review", json=payload, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["registration"]["status"] == "REJECTED"
    assert body["registration"]["rejection_reason"] == "Incomplete documentation and unverifiable business location."
    assert body["business"] is None

    # Verify no business was created
    assert session.query(Business).filter(Business.registration_id == reg.id).count() == 0


def test_admin_cannot_review_already_reviewed_registration(test_client_and_db):
    client, session = test_client_and_db

    reg = BusinessRegistration(
        business_name="Already Handled Cafe",
        category="Cafe",
        contact_name="Aarav",
        email="aarav@cafe.in",
        phone="9876543214",
        address="Indiranagar",
        city="Bengaluru",
        area="Indiranagar",
        pincode="560038",
        status=BusinessRegistrationStatus.APPROVED.value,
    )
    session.add(reg)
    session.commit()

    headers = {"X-Admin-Token": ADMIN_TOKEN}
    payload = {"action": "REJECT", "rejection_reason": "Too late"}
    res = client.post(f"/api/v1/nammadeals/admin/registrations/{reg.id}/review", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Only PENDING registrations can be reviewed" in res.json()["detail"]


# ============================================================================
# 2. Business Profile & Suspension Tests
# ============================================================================

def test_business_owner_get_my_businesses(test_client_and_db):
    client, session = test_client_and_db

    biz1 = Business(
        owner_user_id="usr_owner_alpha",
        name="Alpha Bakery",
        category="Bakery",
        email="alpha@bakery.in",
        phone="9876543215",
        address="Frazer Town",
        city="Bengaluru",
        area="Frazer Town",
        pincode="560005",
        status=BusinessStatus.APPROVED.value,
    )
    biz2 = Business(
        owner_user_id="usr_owner_beta",
        name="Beta Books",
        category="Bookstore",
        email="beta@books.in",
        phone="9876543216",
        address="Church Street",
        city="Bengaluru",
        area="Church Street",
        pincode="560001",
        status=BusinessStatus.APPROVED.value,
    )
    session.add_all([biz1, biz2])
    session.commit()

    headers = {"X-User-ID": "usr_owner_alpha"}
    res = client.get("/api/v1/nammadeals/businesses/me", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["name"] == "Alpha Bakery"


def test_business_suspension_deactivates_campaigns(test_client_and_db):
    client, session = test_client_and_db

    biz = Business(
        owner_user_id="usr_suspension_test",
        name="Suspended Shop",
        category="Retail",
        email="shop@suspend.in",
        phone="9876543217",
        address="Jayanagar 4th Block",
        city="Bengaluru",
        area="Jayanagar",
        pincode="560041",
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz)
    session.commit()

    # Active campaign
    camp = Campaign(
        business_id=biz.id,
        name="Active Weekend Sale",
        campaign_type="DISCOUNT",
        start_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 11, 30, tzinfo=timezone.utc),
        approval_status=CampaignApprovalStatus.APPROVED.value,
        is_active=True,
        targeting_strategy="RADIUS",
        targeting_radius_km=3.0,
        priority=15,
        frequency_limit_per_user=2,
    )
    session.add(camp)
    session.commit()

    # Admin suspends business
    headers = {"X-Admin-Token": ADMIN_TOKEN}
    payload = {"status": "SUSPENDED", "reason": "Policy violation"}
    res = client.patch(f"/api/v1/nammadeals/admin/businesses/{biz.id}/status", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "SUSPENDED"

    # Campaign should have been deactivated automatically
    session.refresh(camp)
    assert camp.is_active is False
