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
from app.services.nammaserve.discovery.cache import (
    DiscoveryResultCache,
    get_default_discovery_cache,
    make_discovery_cache_key,
)
from app.services.nammaserve.discovery.comparison import PriceComparisonEngine
from app.services.nammaserve.discovery.deduplicator import ResultDeduplicator
from app.services.nammaserve.discovery.foursquare import FoursquareDiscoveryConnector
from app.services.nammaserve.discovery.geoapify import GeoapifyDiscoveryConnector
from app.services.nammaserve.discovery.google_places import GooglePlacesDiscoveryConnector
from app.services.nammaserve.discovery.justdial import JustdialDiscoveryConnector
from app.services.nammaserve.discovery.local_db import LocalDBDiscoveryConnector
from app.services.nammaserve.discovery.nobroker import NoBrokerDiscoveryConnector
from app.services.nammaserve.discovery.osm import OpenStreetMapDiscoveryConnector
from app.services.nammaserve.discovery.platform_db import PlatformListingDiscoveryConnector
from app.services.nammaserve.discovery.ranking import DeterministicRankingEngine
from app.services.nammaserve.discovery.resolver import CatalogueResolver
from app.services.nammaserve.discovery.sulekha import SulekhaDiscoveryConnector
from app.services.nammaserve.discovery.urban_company import UrbanCompanyDiscoveryConnector
from app.services.nammaserve.discovery.web_search import WebSearchDiscoveryConnector

logger = logging.getLogger(__name__)


class UnifiedDiscoveryService:
    """Orchestrates local database, platform rate cards, and external source connectors into a unified search."""

    def __init__(
        self,
        db: Session,
        connectors: list[BaseDiscoveryConnector] | None = None,
        cache: DiscoveryResultCache | None = None,
    ):
        self.db = db
        self.cache = cache if cache is not None else get_default_discovery_cache()
        if connectors is not None:
            self.connectors = connectors
        else:
            self.connectors = [
                LocalDBDiscoveryConnector(db=db),
                PlatformListingDiscoveryConnector(db=db),
                GeoapifyDiscoveryConnector(),
                FoursquareDiscoveryConnector(),
                OpenStreetMapDiscoveryConnector(),
                GooglePlacesDiscoveryConnector(),
                UrbanCompanyDiscoveryConnector(),
                NoBrokerDiscoveryConnector(),
                JustdialDiscoveryConnector(),
                SulekhaDiscoveryConnector(),
                WebSearchDiscoveryConnector(),
            ]

    async def discover(self, query: DiscoveryQuery) -> UnifiedDiscoveryResponse:
        """Execute catalogue-aware discovery across all configured connectors with caching."""
        # 1. Resolve query against canonical service catalogue
        if not query.resolved_service_slug and not query.resolved_category_slug:
            resolved = CatalogueResolver.resolve(query.service, db=self.db)
            query.resolved_service_slug = resolved.service_slug
            query.resolved_service_name = resolved.service_name
            query.resolved_category_slug = resolved.category_slug
            query.resolved_category_name = resolved.category_name
            query.service_match_level = resolved.match_level
            query.service_match_confidence = resolved.match_confidence
            query.is_ambiguous = resolved.is_ambiguous
            query.possible_matches = resolved.possible_matches
        elif query.resolved_service_slug and not query.service_match_confidence:
            # Re-confirm confidence if slug was pre-populated
            resolved = CatalogueResolver.resolve(query.resolved_service_slug, db=self.db)
            query.service_match_level = resolved.match_level
            query.service_match_confidence = resolved.match_confidence
            query.is_ambiguous = resolved.is_ambiguous
            query.possible_matches = resolved.possible_matches

        # 2. Check cache for identical queries
        cache_key = make_discovery_cache_key(query)
        cached_results = self.cache.get(cache_key)
        if cached_results is not None:
            logger.debug("Discovery cache hit for key '%s'", cache_key)
            connector_statuses = [
                c.get_status(results_count=len(cached_results) if c.is_available else 0)
                for c in self.connectors
            ]
            cached_comparison = PriceComparisonEngine.build_summary(query, cached_results)
            return UnifiedDiscoveryResponse(
                query=query,
                total_results=len(cached_results),
                connectors_contacted=connector_statuses,
                results=cached_results,
                price_comparison=cached_comparison,
            )

        # 3. Dispatch available connectors in parallel
        tasks = []
        for connector in self.connectors:
            if connector.is_available:
                tasks.append(self._execute_connector_search(connector, query))

        connector_results: list[tuple[BaseDiscoveryConnector, list[NormalizedProviderResult]]] = []
        if tasks:
            executed = await asyncio.gather(*tasks, return_exceptions=True)
            for res in executed:
                if isinstance(res, tuple):
                    connector_results.append(res)
                elif isinstance(res, Exception):
                    logger.error("Connector task execution error: %s", res)

        # 4. Collect raw results and status reports
        all_raw_results: list[NormalizedProviderResult] = []
        connector_statuses: list[ConnectorStatus] = []

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

        # 5. Cross-source conservative deduplication
        deduplicated = ResultDeduplicator.deduplicate(all_raw_results)

        # 6. Transparent deterministic ranking
        ranked = DeterministicRankingEngine.rank_results(deduplicated, query)

        # 7. Apply limit
        limited_results = ranked[: query.limit]

        # 8. Store in cache
        self.cache.set(cache_key, limited_results)

        # 9. Build structured price comparison across all ranked candidates
        price_comparison = PriceComparisonEngine.build_summary(query, ranked)

        return UnifiedDiscoveryResponse(
            query=query,
            total_results=len(limited_results),
            connectors_contacted=connector_statuses,
            results=limited_results,
            price_comparison=price_comparison,
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
