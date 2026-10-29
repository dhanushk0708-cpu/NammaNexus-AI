import logging
from app.models.nammaserve import SourceType
from app.schemas.nammaserve import ConnectorStatus, DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector

logger = logging.getLogger(__name__)


class JustdialDiscoveryConnector(BaseDiscoveryConnector):
    """Honest connector for Justdial business discovery.
    
    Status: Not configured.
    Justdial does not provide an open unauthenticated developer API.
    Third-party scraping is unauthorized and violates terms of service.
    """

    @property
    def name(self) -> str:
        return "Justdial"

    @property
    def source_type(self) -> SourceType:
        return SourceType.JUSTDIAL

    @property
    def is_available(self) -> bool:
        # Commercial licensed credentials are not configured
        return False

    def get_status(self, results_count: int = 0) -> ConnectorStatus:
        return ConnectorStatus(
            connector_name=self.name,
            source_type=self.source_type,
            is_available=self.is_available,
            status_message="Justdial official B2B integration is not publicly available; unauthorized scraping is not permitted.",
            results_count=results_count,
        )

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        return []
