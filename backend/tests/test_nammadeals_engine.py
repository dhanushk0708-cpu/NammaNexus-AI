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
    PromotionEvent,
    PromotionEventType,
    TargetingStrategy,
)


ADMIN_TOKEN = "test-nammadeals-admin-secret-token"
CITIZEN_A = "usr_citizen_arjun"
CITIZEN_B = "usr_citizen_priya"


@pytest.fixture(autouse=True)
def configure_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "nammadeals_admin_token", ADMIN_TOKEN)


@pytest.fixture
def seeded_deals_ecosystem(test_client_and_db):
    """Seed businesses and campaigns across Bengaluru for geospatial and promotion testing."""
    _, session = test_client_and_db
    now = datetime.now(timezone.utc)

    # 1. Koramangala Business & Campaign (Approved, Active)
    biz_kora = Business(
        owner_user_id="usr_biz_kora",
        name="Koramangala Burger Club",
        category="Food & Dining",
        email="burger@kora.in",
        phone="9876543201",
        address="80ft Road, 4th Block, Koramangala",
        city="Bengaluru",
        area="Koramangala",
        pincode="560034",
        latitude=12.9340,
        longitude=77.6220,
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz_kora)
    session.commit()

    camp_kora = Campaign(
        business_id=biz_kora.id,
        name="Koramangala Craft Burgers 30% Off",
        campaign_type="DISCOUNT",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=10),
        approval_status=CampaignApprovalStatus.APPROVED.value,
        is_active=True,
        targeting_strategy=TargetingStrategy.RADIUS.value,
        targeting_radius_km=3.0,
        latitude=12.9340,
        longitude=77.6220,
        priority=25,
        frequency_limit_per_user=2,
    )
    session.add(camp_kora)
    session.commit()

    offer_kora = Offer(
        campaign_id=camp_kora.id,
        title="30% Off Gourmet Burgers",
        discount_type="PERCENTAGE",
        discount_value=30.0,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=10),
        offer_type=OfferType.COUPON.value,
        coupon_code="BURGER30",
        max_redemptions=100,
        is_active=True,
    )
    session.add(offer_kora)

    # 2. Indiranagar Business & Campaign (Approved, Active)
    biz_indira = Business(
        owner_user_id="usr_biz_indira",
        name="Indiranagar Specialty Coffee",
        category="Cafe",
        email="coffee@indira.in",
        phone="9876543202",
        address="100ft Road, Indiranagar",
        city="Bengaluru",
        area="Indiranagar",
        pincode="560038",
        latitude=12.9716,
        longitude=77.6412,
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz_indira)
    session.commit()

    camp_indira = Campaign(
        business_id=biz_indira.id,
        name="Indiranagar Cold Brew BOGO",
        campaign_type="DISCOUNT",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=10),
        approval_status=CampaignApprovalStatus.APPROVED.value,
        is_active=True,
        targeting_strategy=TargetingStrategy.RADIUS.value,
        targeting_radius_km=4.0,
        latitude=12.9716,
        longitude=77.6412,
        priority=20,
        frequency_limit_per_user=3,
    )
    session.add(camp_indira)
    session.commit()

    offer_indira = Offer(
        campaign_id=camp_indira.id,
        title="Buy 1 Get 1 Free Cold Brew",
        discount_type="FREEBIE",
        discount_value=100.0,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=10),
        offer_type=OfferType.COUPON.value,
        coupon_code="COLD100",
        max_redemptions=50,
        is_active=True,
    )
    session.add(offer_indira)

    # 3. City-Wide Campaign
    biz_city = Business(
        owner_user_id="usr_biz_city",
        name="Bengaluru Supermarket Chain",
        category="Groceries",
        email="contact@supermart.in",
        phone="9876543203",
        address="MG Road",
        city="Bengaluru",
        area="Central",
        pincode="560001",
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz_city)
    session.commit()

    camp_city = Campaign(
        business_id=biz_city.id,
        name="All-Bengaluru Grocery Festival",
        campaign_type="DISCOUNT",
        start_date=now - timedelta(days=2),
        end_date=now + timedelta(days=15),
        approval_status=CampaignApprovalStatus.APPROVED.value,
        is_active=True,
        targeting_strategy=TargetingStrategy.CITYWIDE.value,
        priority=10,
        frequency_limit_per_user=5,
    )
    session.add(camp_city)
    session.commit()

    offer_city = Offer(
        campaign_id=camp_city.id,
        title="Flat ₹200 Off on Groceries",
        discount_type="FLAT",
        discount_value=200.0,
        valid_from=now - timedelta(days=2),
        valid_until=now + timedelta(days=15),
        offer_type=OfferType.COUPON.value,
        coupon_code="GROCERY200",
        max_redemptions=200,
        is_active=True,
    )
    session.add(offer_city)

    # 4. Online Campaign
    biz_online = Business(
        owner_user_id="usr_biz_online",
        name="Cloud EdTech Academy",
        category="Education",
        email="learn@edtech.in",
        phone="9876543204",
        address="Virtual",
        city="Bengaluru",
        area="HSR Layout",
        pincode="560102",
        status=BusinessStatus.APPROVED.value,
    )
    session.add(biz_online)
    session.commit()

    camp_online = Campaign(
        business_id=biz_online.id,
        name="Learn Python & AI 50% Off",
        campaign_type="DISCOUNT",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=30),
        approval_status=CampaignApprovalStatus.APPROVED.value,
        is_active=True,
        targeting_strategy=TargetingStrategy.ONLINE.value,
        priority=5,
        frequency_limit_per_user=5,
    )
    session.add(camp_online)
    session.commit()

    offer_online = Offer(
        campaign_id=camp_online.id,
        title="50% Off Online AI Course",
        discount_type="PERCENTAGE",
        discount_value=50.0,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
        offer_type=OfferType.COUPON.value,
        coupon_code="AI50",
        max_redemptions=500,
        is_active=True,
    )
    session.add(offer_online)

    # 5. Suspended Business Campaign (Must NEVER be returned)
    biz_suspended = Business(
        owner_user_id="usr_biz_bad",
        name="Fraudulent Electronics",
        category="Electronics",
        email="bad@fraud.in",
        phone="9876543205",
        address="Unknown",
        city="Bengaluru",
        area="Koramangala",
        pincode="560034",
        status=BusinessStatus.SUSPENDED.value,
    )
    session.add(biz_suspended)
    session.commit()

    camp_suspended = Campaign(
        business_id=biz_suspended.id,
        name="Fake 90% Off Sale",
        campaign_type="DISCOUNT",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=10),
        approval_status=CampaignApprovalStatus.APPROVED.value,
        is_active=True,  # Even if mistakenly set to active, engine must reject
        targeting_strategy=TargetingStrategy.CITYWIDE.value,
    )
    session.add(camp_suspended)
    session.commit()

    offer_suspended = Offer(
        campaign_id=camp_suspended.id,
        title="Fake 90% Off",
        discount_type="PERCENTAGE",
        discount_value=90.0,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=10),
        offer_type=OfferType.COUPON.value,
        coupon_code="FAKE90",
        is_active=True,
    )
    session.add(offer_suspended)

    # 6. Expired Campaign (Must NEVER be returned)
    camp_expired = Campaign(
        business_id=biz_kora.id,
        name="Last Month Expired Promo",
        campaign_type="DISCOUNT",
        start_date=now - timedelta(days=40),
        end_date=now - timedelta(days=10),
        approval_status=CampaignApprovalStatus.APPROVED.value,
        is_active=True,
        targeting_strategy=TargetingStrategy.CITYWIDE.value,
    )
    session.add(camp_expired)
    session.commit()

    offer_expired = Offer(
        campaign_id=camp_expired.id,
        title="Old Offer",
        discount_type="PERCENTAGE",
        discount_value=10.0,
        valid_from=now - timedelta(days=40),
        valid_until=now - timedelta(days=10),
        offer_type=OfferType.COUPON.value,
        coupon_code="OLD10",
        is_active=True,
    )
    session.add(offer_expired)
    session.commit()

    return {
        "camp_kora": camp_kora,
        "camp_indira": camp_indira,
        "camp_city": camp_city,
        "camp_online": camp_online,
        "camp_suspended": camp_suspended,
        "camp_expired": camp_expired,
        "biz_kora": biz_kora,
        "biz_indira": biz_indira,
    }


# ============================================================================
# 1. Location Matching & Promotion Selection Tests
# ============================================================================

def test_promotion_selection_complaint_location(test_client_and_db, seeded_deals_ecosystem):
    client, _ = test_client_and_db

    # Citizen files complaint in Koramangala (12.9345, 77.6225)
    payload = {
        "location_policy": "COMPLAINT_ONLY",
        "complaint_location": {
            "latitude": 12.9345,
            "longitude": 77.6225,
            "area": "Koramangala 4th Block",
        },
        "limit": 3,
    }
    res = client.post("/api/v1/nammadeals/promotions/select", json=payload, headers={"X-User-ID": CITIZEN_A})
    assert res.status_code == 200
    data = res.json()
    assert data["total_selected"] >= 1
    # First recommendation should be Koramangala campaign
    first = data["promotions"][0]
    assert first["campaign_id"] == seeded_deals_ecosystem["camp_kora"].id
    assert first["matched_location_source"] == "COMPLAINT"
    assert first["distance_km"] is not None
    assert first["distance_km"] <= 1.0  # Within ~100 meters
    assert len(first["offers"]) >= 1


def test_promotion_selection_profile_location(test_client_and_db, seeded_deals_ecosystem):
    client, _ = test_client_and_db

    # Citizen profile is in Indiranagar
    payload = {
        "location_policy": "PROFILE_ONLY",
        "profile_location": {
            "city": "Bengaluru",
            "area": "Indiranagar",
            "pincode": "560038",
            "latitude": 12.9720,
            "longitude": 77.6410,
        },
        "limit": 3,
    }
    res = client.post("/api/v1/nammadeals/promotions/select", json=payload, headers={"X-User-ID": CITIZEN_A})
    assert res.status_code == 200
    data = res.json()
    assert data["total_selected"] >= 1
    first = data["promotions"][0]
    assert first["campaign_id"] == seeded_deals_ecosystem["camp_indira"].id
    assert first["matched_location_source"] == "PROFILE"


def test_combined_targeting_evaluates_both_sources(test_client_and_db, seeded_deals_ecosystem):
    client, _ = test_client_and_db

    payload = {
        "location_policy": "COMBINED",
        "complaint_location": {
            "latitude": 12.9340,
            "longitude": 77.6220,
            "area": "Koramangala",
        },
        "profile_location": {
            "latitude": 12.9716,
            "longitude": 77.6412,
            "area": "Indiranagar",
            "pincode": "560038",
        },
        "limit": 3,
    }
    res = client.post("/api/v1/nammadeals/promotions/select", json=payload, headers={"X-User-ID": CITIZEN_A})
    assert res.status_code == 200
    data = res.json()
    campaign_ids = [p["campaign_id"] for p in data["promotions"]]
    # Should include both Koramangala and Indiranagar promotions
    assert seeded_deals_ecosystem["camp_kora"].id in campaign_ids
    assert seeded_deals_ecosystem["camp_indira"].id in campaign_ids
    assert "COMPLAINT" in data["location_sources_evaluated"]
    assert "PROFILE" in data["location_sources_evaluated"]


def test_fallback_to_profile_when_complaint_location_has_no_local_deals(
    test_client_and_db, seeded_deals_ecosystem
):
    client, _ = test_client_and_db

    # Complaint is in Yelahanka (far north, ~25km away, no local campaigns)
    payload = {
        "location_policy": "PREFER_COMPLAINT",
        "complaint_location": {
            "latitude": 13.1007,
            "longitude": 77.5963,
            "area": "Yelahanka",
        },
        "profile_location": {
            "latitude": 12.9340,
            "longitude": 77.6220,
            "area": "Koramangala",
        },
        "limit": 2,
    }
    res = client.post("/api/v1/nammadeals/promotions/select", json=payload, headers={"X-User-ID": CITIZEN_A})
    assert res.status_code == 200
    data = res.json()
    campaign_ids = [p["campaign_id"] for p in data["promotions"]]
    # Successfully fell back to profile location (Koramangala)
    assert seeded_deals_ecosystem["camp_kora"].id in campaign_ids


def test_citywide_and_online_fallback_when_no_local_deals_match(
    test_client_and_db, seeded_deals_ecosystem
):
    client, _ = test_client_and_db

    # Remote location with neither local complaint nor local profile deals
    payload = {
        "location_policy": "COMPLAINT_ONLY",
        "complaint_location": {
            "latitude": 13.3000,
            "longitude": 77.2000,
            "area": "Distant Outskirts",
        },
        "limit": 3,
    }
    res = client.post("/api/v1/nammadeals/promotions/select", json=payload, headers={"X-User-ID": CITIZEN_A})
    assert res.status_code == 200
    data = res.json()
    # Falls back to CITYWIDE and ONLINE campaigns
    sources = [p["matched_location_source"] for p in data["promotions"]]
    assert "CITYWIDE" in sources
    assert "ONLINE" in sources


def test_never_shows_suspended_or_expired_campaigns(test_client_and_db, seeded_deals_ecosystem):
    client, _ = test_client_and_db

    payload = {
        "location_policy": "COMBINED",
        "complaint_location": {"latitude": 12.9340, "longitude": 77.6220},
        "limit": 10,
    }
    res = client.post("/api/v1/nammadeals/promotions/select", json=payload, headers={"X-User-ID": CITIZEN_A})
    assert res.status_code == 200
    data = res.json()
    returned_campaign_ids = {p["campaign_id"] for p in data["promotions"]}
    assert seeded_deals_ecosystem["camp_suspended"].id not in returned_campaign_ids
    assert seeded_deals_ecosystem["camp_expired"].id not in returned_campaign_ids


def test_deduplication_never_shows_duplicate_campaigns_or_businesses(
    test_client_and_db, seeded_deals_ecosystem
):
    client, _ = test_client_and_db

    payload = {
        "location_policy": "COMBINED",
        "complaint_location": {"latitude": 12.9340, "longitude": 77.6220, "area": "Koramangala"},
        "profile_location": {"latitude": 12.9340, "longitude": 77.6220, "area": "Koramangala"},
        "limit": 5,
    }
    res = client.post("/api/v1/nammadeals/promotions/select", json=payload, headers={"X-User-ID": CITIZEN_A})
    assert res.status_code == 200
    promos = res.json()["promotions"]
    camp_ids = [p["campaign_id"] for p in promos]
    biz_names = [p["business_name"] for p in promos]
    assert len(camp_ids) == len(set(camp_ids)), "Duplicate campaigns returned in single selection response"
    assert len(biz_names) == len(set(biz_names)), "Duplicate businesses returned in single selection response"


# ============================================================================
# 2. Frequency Capping & Deterministic Rotation Tests
# ============================================================================

def test_frequency_capping_per_user_limit(test_client_and_db, seeded_deals_ecosystem):
    client, _ = test_client_and_db
    kora_camp_id = seeded_deals_ecosystem["camp_kora"].id  # frequency_limit_per_user = 2

    headers = {"X-User-ID": CITIZEN_A}
    select_payload = {
        "location_policy": "COMPLAINT_ONLY",
        "complaint_location": {"latitude": 12.9340, "longitude": 77.6220},
        "limit": 3,
    }

    # 1. Before hitting frequency limit, campaign is returned
    res1 = client.post("/api/v1/nammadeals/promotions/select", json=select_payload, headers=headers)
    ids1 = [p["campaign_id"] for p in res1.json()["promotions"]]
    assert kora_camp_id in ids1

    # Record 1st impression
    client.post(
        "/api/v1/nammadeals/promotions/events",
        json={"event_type": "IMPRESSION", "campaign_id": kora_camp_id, "idempotency_key": "imp_1"},
        headers=headers,
    )

    # Record 2nd impression
    client.post(
        "/api/v1/nammadeals/promotions/events",
        json={"event_type": "IMPRESSION", "campaign_id": kora_camp_id, "idempotency_key": "imp_2"},
        headers=headers,
    )

    # 2. Now citizen A has hit the frequency cap (2 impressions)
    res_capped = client.post("/api/v1/nammadeals/promotions/select", json=select_payload, headers=headers)
    ids_capped = [p["campaign_id"] for p in res_capped.json()["promotions"]]
    assert kora_camp_id not in ids_capped

    # 3. But another citizen B has NOT hit the frequency cap and still receives it
    res_b = client.post(
        "/api/v1/nammadeals/promotions/select",
        json=select_payload,
        headers={"X-User-ID": CITIZEN_B},
    )
    ids_b = [p["campaign_id"] for p in res_b.json()["promotions"]]
    assert kora_camp_id in ids_b


# ============================================================================
# 3. Event Tracking & Anti-Duplicate Protection
# ============================================================================

def test_record_impression_and_click_events(test_client_and_db, seeded_deals_ecosystem):
    client, session = test_client_and_db
    camp_id = seeded_deals_ecosystem["camp_kora"].id
    headers = {"X-User-ID": CITIZEN_A}

    # Record impression
    imp_res = client.post(
        "/api/v1/nammadeals/promotions/events",
        json={
            "event_type": "IMPRESSION",
            "campaign_id": camp_id,
            "location_source": "COMPLAINT",
        },
        headers=headers,
    )
    assert imp_res.status_code == 201
    assert imp_res.json()["event_type"] == "IMPRESSION"

    # Record click
    click_res = client.post(
        "/api/v1/nammadeals/promotions/events",
        json={
            "event_type": "CLICK",
            "campaign_id": camp_id,
            "location_source": "COMPLAINT",
        },
        headers=headers,
    )
    assert click_res.status_code == 201
    assert click_res.json()["event_type"] == "CLICK"


def test_idempotency_and_debounce_prevent_duplicate_event_submissions(
    test_client_and_db, seeded_deals_ecosystem
):
    client, session = test_client_and_db
    camp_id = seeded_deals_ecosystem["camp_kora"].id
    headers = {"X-User-ID": CITIZEN_A}

    # 1. Idempotent submission
    idemp_key = "idemp_unique_event_test_123"
    payload = {
        "event_type": "CLICK",
        "campaign_id": camp_id,
        "idempotency_key": idemp_key,
    }

    res1 = client.post("/api/v1/nammadeals/promotions/events", json=payload, headers=headers)
    assert res1.status_code == 201
    event_id_1 = res1.json()["id"]

    res2 = client.post("/api/v1/nammadeals/promotions/events", json=payload, headers=headers)
    assert res2.status_code == 201
    event_id_2 = res2.json()["id"]

    # Same event ID returned (deduplicated)
    assert event_id_1 == event_id_2

    # Database only contains 1 record for this idempotency key
    count = session.query(PromotionEvent).filter(PromotionEvent.idempotency_key == idemp_key).count()
    assert count == 1


def test_missing_location_handled_gracefully(test_client_and_db, seeded_deals_ecosystem):
    client, _ = test_client_and_db

    # Request with no coordinates, empty locations
    payload = {
        "location_policy": "COMBINED",
        "limit": 3,
    }
    res = client.post("/api/v1/nammadeals/promotions/select", json=payload, headers={"X-User-ID": CITIZEN_A})
    assert res.status_code == 200
    data = res.json()
    # Still returns fallback campaigns (CITYWIDE, ONLINE) without error
    assert data["total_selected"] >= 1


def test_get_promotion_details_endpoint(test_client_and_db, seeded_deals_ecosystem):
    client, _ = test_client_and_db
    camp_id = seeded_deals_ecosystem["camp_kora"].id

    res = client.get(f"/api/v1/nammadeals/promotions/{camp_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["campaign_name"] == "Koramangala Craft Burgers 30% Off"
    assert data["business_name"] == "Koramangala Burger Club"
    assert len(data["offers"]) >= 1


# ============================================================================
# 4. SpotFix Independence & Failure Isolation
# ============================================================================

def test_spotfix_independence_from_nammadeals(test_client_and_db, monkeypatch):
    """Verifies that SpotFix complaint lifecycle is completely decoupled from NammaDeals."""
    client, session = test_client_and_db

    # 1. Create a SpotFix complaint
    spotfix_payload = {
        "category": "POTHOLE",
        "description": "Deep dangerous pothole on 80ft road.",
        "latitude": 12.9340,
        "longitude": 77.6220,
    }
    spotfix_res = client.post("/api/v1/spotfix/complaints", json=spotfix_payload)
    assert spotfix_res.status_code == 201
    complaint_data = spotfix_res.json()
    assert complaint_data["status"] == "DRAFT"
    assert complaint_data["id"] is not None

    # 2. Simulate NammaDeals promotion engine failure
    from app.services.nammadeals import selection as selection_service
    def mock_failing_selection(*args, **kwargs):
        raise RuntimeError("Database connection pool exhausted in NammaDeals")

    monkeypatch.setattr(selection_service, "select_promotions", mock_failing_selection)

    # Calling promotion select fails gracefully with 500 error
    deals_res = client.post(
        "/api/v1/nammadeals/promotions/select",
        json={
            "location_policy": "COMPLAINT_ONLY",
            "complaint_location": {
                "latitude": complaint_data["latitude"],
                "longitude": complaint_data["longitude"],
            },
        },
    )
    assert deals_res.status_code == 500
    assert "Promotion selection failed" in deals_res.json()["detail"]

    # 3. But SpotFix complaint remains completely safe and accessible
    spotfix_get = client.get(f"/api/v1/spotfix/complaints/{complaint_data['id']}")
    assert spotfix_get.status_code == 200
    assert spotfix_get.json()["id"] == complaint_data["id"]

