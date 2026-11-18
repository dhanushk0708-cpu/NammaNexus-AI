from datetime import datetime, timedelta, timezone
import pytest
from app.core.config import settings
from app.models.nammadeals import (
    Business,
    BusinessStatus,
    Campaign,
    CampaignApprovalStatus,
    Offer,
)


ADMIN_TOKEN = "nammadeals-secure-admin-token-xyz"
USER_A = "usr_tenant_alice"
USER_B = "usr_tenant_bob"


@pytest.fixture(autouse=True)
def configure_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "nammadeals_admin_token", ADMIN_TOKEN)


@pytest.fixture
def business_a(test_client_and_db):
    _, session = test_client_and_db
    biz = Business(
        owner_user_id=USER_A,
        name="Alice Artisan Bakery",
        category="Bakery",
        email="alice@bakery.in",
        phone="9876543230",
        address="Lavelle Road",
        city="Bengaluru",
        area="Shanthala Nagar",
        pincode="560001",
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz)
    session.commit()
    session.refresh(biz)
    return biz


def test_cross_tenant_isolation_business_access(test_client_and_db, business_a):
    client, _ = test_client_and_db

    # User B tries to view User A's business
    res = client.get(f"/api/v1/nammadeals/businesses/{business_a.id}", headers={"X-User-ID": USER_B})
    assert res.status_code == 403
    assert "You do not have permission" in res.json()["detail"]

    # User B tries to update User A's business
    res_patch = client.patch(
        f"/api/v1/nammadeals/businesses/{business_a.id}",
        json={"name": "Hacked Bakery"},
        headers={"X-User-ID": USER_B},
    )
    assert res_patch.status_code == 403


def test_cross_tenant_isolation_campaign_and_offer_access(test_client_and_db, business_a):
    client, session = test_client_and_db
    now = datetime.now(timezone.utc)

    camp_a = Campaign(
        business_id=business_a.id,
        name="Alice Croissant Deal",
        campaign_type="DISCOUNT",
        start_date=now,
        end_date=now + timedelta(days=10),
        approval_status=CampaignApprovalStatus.DRAFT.value,
    )
    session.add(camp_a)
    session.commit()
    session.refresh(camp_a)

    offer_a = Offer(
        campaign_id=camp_a.id,
        title="20% Off Almond Croissant",
        discount_type="PERCENTAGE",
        discount_value=20.0,
        valid_from=now,
        valid_until=now + timedelta(days=10),
        offer_type="COUPON",
        coupon_code="ALMOND20",
    )
    session.add(offer_a)
    session.commit()
    session.refresh(offer_a)

    headers_b = {"X-User-ID": USER_B}

    # 1. User B tries to create campaign under Business A
    res_create_camp = client.post(
        f"/api/v1/nammadeals/businesses/{business_a.id}/campaigns",
        json={"name": "Bob's Takeover", "start_date": now.isoformat(), "end_date": (now + timedelta(days=5)).isoformat()},
        headers=headers_b,
    )
    assert res_create_camp.status_code == 403

    # 2. User B tries to view Campaign A
    res_view_camp = client.get(f"/api/v1/nammadeals/campaigns/{camp_a.id}", headers=headers_b)
    assert res_view_camp.status_code == 403

    # 3. User B tries to update Campaign A
    res_update_camp = client.patch(
        f"/api/v1/nammadeals/campaigns/{camp_a.id}",
        json={"name": "Modified by Bob"},
        headers=headers_b,
    )
    assert res_update_camp.status_code == 403

    # 4. User B tries to add offer to Campaign A
    res_add_offer = client.post(
        f"/api/v1/nammadeals/campaigns/{camp_a.id}/offers",
        json={
            "title": "Bob's Offer",
            "discount_type": "PERCENTAGE",
            "discount_value": 50.0,
            "valid_from": now.isoformat(),
            "valid_until": (now + timedelta(days=5)).isoformat(),
            "offer_type": "COUPON",
            "coupon_code": "BOB50",
        },
        headers=headers_b,
    )
    assert res_add_offer.status_code == 403

    # 5. User B tries to update Offer A
    res_update_offer = client.patch(
        f"/api/v1/nammadeals/offers/{offer_a.id}",
        json={"title": "Hacked Offer"},
        headers=headers_b,
    )
    assert res_update_offer.status_code == 403


def test_admin_endpoints_require_valid_admin_token(test_client_and_db):
    client, _ = test_client_and_db

    # Missing token -> 401
    res_no_token = client.get("/api/v1/nammadeals/admin/registrations")
    assert res_no_token.status_code == 401

    # Invalid token -> 403
    res_bad_token = client.get(
        "/api/v1/nammadeals/admin/registrations",
        headers={"X-Admin-Token": "invalid-wrong-admin-token"},
    )
    assert res_bad_token.status_code == 403

    # Valid token -> 200
    res_ok = client.get(
        "/api/v1/nammadeals/admin/registrations",
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    assert res_ok.status_code == 200


def test_payment_recording_and_admin_verification(test_client_and_db, business_a):
    client, _ = test_client_and_db
    headers_a = {"X-User-ID": USER_A}
    admin_headers = {"X-Admin-Token": ADMIN_TOKEN}
    now = datetime.now(timezone.utc)

    # 1. User A records payment
    pay_payload = {
        "amount": 5000.0,
        "currency": "INR",
        "transaction_id": "TXN_UPI_987654321_ABC",
        "payment_method": "UPI",
        "payment_date": now.isoformat(),
    }
    res_pay = client.post(f"/api/v1/nammadeals/businesses/{business_a.id}/payments", json=pay_payload, headers=headers_a)
    assert res_pay.status_code == 201
    pay_data = res_pay.json()
    assert pay_data["verification_status"] == "PENDING"
    assert pay_data["amount"] == 5000.0

    # 2. Duplicate transaction_id fails
    dup_res = client.post(f"/api/v1/nammadeals/businesses/{business_a.id}/payments", json=pay_payload, headers=headers_a)
    assert dup_res.status_code == 400
    assert "already been recorded" in dup_res.json()["detail"]

    # 3. User B cannot view User A's payments
    res_b_view = client.get(f"/api/v1/nammadeals/businesses/{business_a.id}/payments", headers={"X-User-ID": USER_B})
    assert res_b_view.status_code == 403

    # 4. Admin lists and verifies payment
    res_admin_list = client.get("/api/v1/nammadeals/admin/payments", headers=admin_headers)
    assert res_admin_list.status_code == 200
    assert len(res_admin_list.json()) >= 1

    res_verify = client.post(
        f"/api/v1/nammadeals/admin/payments/{pay_data['id']}/verify",
        json={"action": "VERIFY", "admin_notes": "Bank statement confirmed."},
        headers=admin_headers,
    )
    assert res_verify.status_code == 200
    assert res_verify.json()["verification_status"] == "VERIFIED"
    assert res_verify.json()["admin_notes"] == "Bank statement confirmed."
