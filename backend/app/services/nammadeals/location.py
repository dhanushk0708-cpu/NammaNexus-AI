import logging
from typing import Any

from app.models.nammadeals import Campaign, TargetingStrategy
from app.services.nammaserve.discovery.distance import haversine_distance_km

logger = logging.getLogger(__name__)


def evaluate_location_match(
    campaign: Campaign,
    latitude: float | None = None,
    longitude: float | None = None,
    area: str | None = None,
    pincode: str | None = None,
    city: str | None = None,
    allow_nearby_expansion: bool = False,
    allow_citywide: bool = False,
    allow_online: bool = False,
) -> tuple[bool, float | None, str | None]:
    """Evaluates whether a campaign matches a given location context.

    Returns:
        (is_match, distance_km, match_type)
    """
    strategy = campaign.targeting_strategy

    # 1. Online campaign targeting strategy
    if strategy == TargetingStrategy.ONLINE.value:
        if allow_online:
            return True, None, "ONLINE"
        return False, None, None

    # 2. City-wide targeting strategy
    if strategy == TargetingStrategy.CITYWIDE.value:
        if allow_citywide:
            business_city = (campaign.business.city or "Bengaluru").strip().lower()
            target_city = (city or "Bengaluru").strip().lower()
            if target_city == business_city or not city:
                return True, None, "CITYWIDE"
        return False, None, None

    # 3. Coordinate-based radius check
    target_lat = campaign.latitude if campaign.latitude is not None else campaign.business.latitude
    target_lng = campaign.longitude if campaign.longitude is not None else campaign.business.longitude

    if (
        latitude is not None
        and longitude is not None
        and target_lat is not None
        and target_lng is not None
    ):
        try:
            dist = haversine_distance_km(latitude, longitude, target_lat, target_lng)
            if dist <= campaign.targeting_radius_km:
                return True, dist, "RADIUS"
            if allow_nearby_expansion and dist <= max(campaign.targeting_radius_km * 2.0, 10.0):
                return True, dist, "NEARBY"
        except Exception as e:
            logger.warning("Error calculating haversine distance for campaign %s: %s", campaign.id, e)

    # 4. Deterministic locality/area and pincode matching (when coords missing or outside strict radius)
    if pincode and campaign.business.pincode:
        clean_user_pin = pincode.strip()
        clean_biz_pin = campaign.business.pincode.strip()
        if clean_user_pin == clean_biz_pin:
            return True, None, "PINCODE"

    if area and campaign.business.area:
        norm_user_area = area.strip().lower()
        norm_biz_area = campaign.business.area.strip().lower()
        if norm_user_area in norm_biz_area or norm_biz_area in norm_user_area:
            return True, None, "AREA"

    return False, None, None
