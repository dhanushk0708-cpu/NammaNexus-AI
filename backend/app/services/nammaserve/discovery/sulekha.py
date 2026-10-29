import logging
from app.models.nammaserve import SourceType
from app.schemas.nammaserve import ConnectorStatus, DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector

logger = logging.getLogger(__name__)


class SulekhaDiscoveryConnector(BaseDiscoveryConnector):
    """Honest connector for Sulekha service discovery.
    
    Status: Not configured.
    Sulekha requires an authorized commercial partner integration.
    Automated unauthenticated scraping is not supported or permitted.
    """

    @property
    def name(self) -> str:
        return "Sulekha"

    @property
    def source_type(self) -> SourceType:
        return SourceType.SULEKHA

    @property
    def is_available(self) -> bool:
        # Commercial partner credentials are not configured
        return False

    def get_status(self, results_count: int = 0) -> ConnectorStatus:
        return ConnectorStatus(
            connector_name=self.name,
            source_type=self.source_type,
            is_available=self.is_available,
            status_message="Sulekha partner integration requires authorized commercial credentials.",
            results_count=results_count,
        )

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        return []
