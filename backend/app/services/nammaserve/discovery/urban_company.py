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
        # Urban Company public partner API requires commercial enterprise agreement
        return False

    def get_status(self, results_count: int = 0):
        from app.schemas.nammaserve import ConnectorStatus
        return ConnectorStatus(
            connector_name=self.name,
            source_type=self.source_type,
            is_available=self.is_available,
            status_message="Urban Company public partner API requires commercial enterprise agreement; connector is not configured and unapproved scraping is prohibited.",
            results_count=results_count,
        )

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        return []
