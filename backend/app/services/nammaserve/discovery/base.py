from abc import ABC, abstractmethod

from app.models.nammaserve import SourceType
from app.schemas.nammaserve import ConnectorStatus, DiscoveryQuery, NormalizedProviderResult


class BaseDiscoveryConnector(ABC):
    """Abstract base connector for civic service discovery sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the connector (e.g., 'Local Database', 'Google Places')."""
        pass

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Source type identifier."""
        pass

    @property
    def is_available(self) -> bool:
        """Whether this connector is configured and ready for live querying."""
        return True

    @abstractmethod
    async def search(self, query: DiscoveryQuery) -> list[NormalizedProviderResult]:
        """Execute search against the data source and return normalized provider results."""
        pass

    def get_status(self, results_count: int = 0) -> ConnectorStatus:
        """Return human-readable connector status."""
        if not self.is_available:
            return ConnectorStatus(
                connector_name=self.name,
                source_type=self.source_type,
                is_available=False,
                status_message=f"{self.name} is not configured or publicly accessible.",
                results_count=0,
            )
        return ConnectorStatus(
            connector_name=self.name,
            source_type=self.source_type,
            is_available=True,
            status_message=f"Successfully queried {self.name}.",
            results_count=results_count,
        )
