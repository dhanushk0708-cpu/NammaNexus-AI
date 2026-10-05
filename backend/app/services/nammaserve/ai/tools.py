from typing import Any
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.models.nammaserve import Provider, ProviderService
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.discovery.service import UnifiedDiscoveryService


class SearchServicesInput(BaseModel):
    service: str | None = Field(
        default=None,
        description="Service category slug or name (e.g. water-tanker, locksmith-emergency).",
    )
    location: str | None = Field(
        default=None,
        description="Bengaluru area / locality name (e.g. Kengeri, Indiranagar, HSR Layout).",
    )
    lat: float | None = Field(default=None, description="Citizen latitude.")
    lng: float | None = Field(default=None, description="Citizen longitude.")
    radius_km: float = Field(default=5.0, description="Search radius in km.")
    urgent: bool = Field(default=False, description="Emergency or 24x7 requirement.")
    verified_only: bool = Field(default=False, description="Only return verified providers.")
    limit: int = Field(default=10, description="Max results.")


class GetProviderInput(BaseModel):
    provider_id: str = Field(..., description="The unique UUID ID of the provider.")


def create_search_services_tool(db: Session, discovery_service: UnifiedDiscoveryService | None = None) -> StructuredTool:
    """Creates a deterministic LangChain tool for civic service discovery."""
    active_discovery = discovery_service or UnifiedDiscoveryService(db=db)

    async def _search_services_func(
        service: str | None = None,
        location: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_km: float = 5.0,
        urgent: bool = False,
        verified_only: bool = False,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        query = DiscoveryQuery(
            service=service,
            area=location,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            emergency_only=urgent,
            verified_only=verified_only,
            limit=limit,
        )
        response = await active_discovery.discover(query)
        return [result.model_dump() for result in response.results]

    return StructuredTool.from_function(
        coroutine=_search_services_func,
        name="search_local_services",
        description="Search for local civic services, water tankers, locksmiths, repair, e-waste, debris pickup in Bengaluru.",
        args_schema=SearchServicesInput,
    )


def create_get_provider_tool(db: Session) -> StructuredTool:
    """Creates a deterministic LangChain tool for retrieving specific provider details."""

    async def _get_provider_func(provider_id: str) -> dict[str, Any] | None:
        provider = (
            db.query(Provider)
            .filter(Provider.id == provider_id)
            .options(
                joinedload(Provider.services).joinedload(ProviderService.category),
                joinedload(Provider.service_areas),
            )
            .first()
        )
        if not provider:
            return None

        return {
            "id": provider.id,
            "name": provider.name,
            "phone": provider.phone,
            "address": provider.address,
            "primary_area": provider.primary_area,
            "operating_hours": provider.operating_hours,
            "is_emergency_service": provider.is_emergency_service,
            "verification_status": provider.verification_status,
            "services": [
                {
                    "category": svc.category.name if svc.category else None,
                    "price_min": svc.price_min,
                    "price_max": svc.price_max,
                    "price_unit": svc.price_unit,
                    "water_type": svc.water_type,
                    "capacity": svc.capacity,
                    "availability": svc.availability,
                }
                for svc in provider.services
            ],
        }

    return StructuredTool.from_function(
        coroutine=_get_provider_func,
        name="get_provider",
        description="Retrieve complete verified details and rate card for a specific provider by provider_id.",
        args_schema=GetProviderInput,
    )
