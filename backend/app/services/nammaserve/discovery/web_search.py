from app.models.nammaserve import SourceType
from app.schemas.nammaserve import DiscoveryQuery, NormalizedProviderResult
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector


class WebSearchDiscoveryConnector(BaseDiscoveryConnector):
    """Placeholder connector for Public Web Search sources."""

    @property
    def name(self) -> str:
        return "Public Web Directory"

    @property
    def source_type(self) -> SourceType:
        return SourceType.WEB

    @property
    def is_available(self) -> bool:
        return False

    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        return []
