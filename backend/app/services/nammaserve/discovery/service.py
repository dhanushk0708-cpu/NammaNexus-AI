import asyncio
import logging
from sqlalchemy.orm import Session

from app.schemas.nammaserve import (
    ConnectorStatus,
    DiscoveryQuery,
    NormalizedProviderResult,
    UnifiedDiscoveryResponse,
)
from app.services.nammaserve.discovery.base import BaseDiscoveryConnector
from app.services.nammaserve.discovery.deduplicator import ResultDeduplicator
from app.services.nammaserve.discovery.google_places import GooglePlacesDiscoveryConnector
from app.services.nammaserve.discovery.local_db import LocalDBDiscoveryConnector
from app.services.nammaserve.discovery.nobroker import NoBrokerDiscoveryConnector
from app.services.nammaserve.discovery.ranking import DeterministicRankingEngine
from app.services.nammaserve.discovery.urban_company import UrbanCompanyDiscoveryConnector
from app.services.nammaserve.discovery.web_search import WebSearchDiscoveryConnector

logger = logging.getLogger(__name__)


class UnifiedDiscoveryService:
    """Orchestrates local database and external source connectors into a single unified search."""

    def __init__(self, db: Session, connectors: list[BaseDiscoveryConnector] | None = None):
        self.db = db
        if connectors is not None:
            self.connectors = connectors
        else:
            self.connectors = [
                LocalDBDiscoveryConnector(db=db),
                GooglePlacesDiscoveryConnector(),
                UrbanCompanyDiscoveryConnector(),
                NoBrokerDiscoveryConnector(),
                WebSearchDiscoveryConnector(),
            ]

    async def discover(self, query: DiscoveryQuery) -> UnifiedDiscoveryResponse:
        """Execute discovery across all configured connectors."""
        tasks = []
        for connector in self.connectors:
            if connector.is_available:
                tasks.append(self._execute_connector_search(connector, query))

        # Run available connectors in parallel
        connector_results: list[tuple[BaseDiscoveryConnector, list[NormalizedProviderResult]]] = []
        if tasks:
            executed = await asyncio.gather(*tasks, return_exceptions=True)
            for res in executed:
                if isinstance(res, tuple):
                    connector_results.append(res)
                elif isinstance(res, Exception):
                    logger.error("Connector task execution error: %s", res)

        # Collect raw results and status reports
        all_raw_results: list[NormalizedProviderResult] = []
        connector_statuses: list[ConnectorStatus] = []

        # Map executed results by connector name
        results_by_connector = {
            conn.name: res_list for conn, res_list in connector_results
        }

        for connector in self.connectors:
            if connector.is_available:
                res_list = results_by_connector.get(connector.name, [])
                all_raw_results.extend(res_list)
                connector_statuses.append(connector.get_status(results_count=len(res_list)))
            else:
                connector_statuses.append(connector.get_status(results_count=0))

        # Deduplicate
        deduplicated = ResultDeduplicator.deduplicate(all_raw_results)

        # Rank
        ranked = DeterministicRankingEngine.rank_results(deduplicated, query)

        # Slice limit
        limited_results = ranked[: query.limit]

        return UnifiedDiscoveryResponse(
            query=query,
            total_results=len(limited_results),
            connectors_contacted=connector_statuses,
            results=limited_results,
        )

    async def _execute_connector_search(
        self, connector: BaseDiscoveryConnector, query: DiscoveryQuery
    ) -> tuple[BaseDiscoveryConnector, list[NormalizedProviderResult]]:
        try:
            results = await connector.search(query)
            return (connector, results)
        except Exception as exc:
            logger.error("Connector %s failed: %s", connector.name, exc)
            return (connector, [])
