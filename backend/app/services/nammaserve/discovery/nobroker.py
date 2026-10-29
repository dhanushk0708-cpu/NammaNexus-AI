from app.models.nammaserve import SourceType
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector


class NoBrokerDiscoveryConnector(BaseDiscoveryConnector):
    """Placeholder connector for NoBroker Services.

    Preserves connector architecture without scraping or assuming private API access.
    """

    @property
    def name(self) -> str:
        return "NoBroker"

    @property
    def source_type(self) -> SourceType:
        return SourceType.NOBROKER

    @property
    def is_available(self) -> bool:
        # NoBroker partner API is not publicly accessible
        return False

    def get_status(self, results_count: int = 0):
        from app.schemas.nammaserve import ConnectorStatus
        return ConnectorStatus(
            connector_name=self.name,
            source_type=self.source_type,
            is_available=self.is_available,
            status_message="NoBroker partner API is not publicly accessible; connector is not configured and private API bypassing is prohibited.",
            results_count=results_count,
        )

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        return []
