from app.models.nammaserve import SourceType
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector


class UrbanCompanyDiscoveryConnector(BaseDiscoveryConnector):
    """Placeholder connector for Urban Company.

    Preserves connector architecture without scraping or assuming private API access.
    """

    @property
    def name(self) -> str:
        return "Urban Company"

    @property
    def source_type(self) -> SourceType:
        return SourceType.URBAN_COMPANY

    @property
    def is_available(self) -> bool:
        # Public partner API is not currently configured / authorized
        return False

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        return []
