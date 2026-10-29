from app.schemas.nammaserve import DiscoveryQuery
from app.services.nammaserve.discovery.cache import make_discovery_cache_key
from app.services.nammaserve.discovery.resolver import CatalogueResolver
from sqlalchemy.exc import OperationalError


def test_discovery_cache_key_separates_result_limits():
    common = dict(service="plumbing", area="Rajajinagar", lat=12.9915, lng=77.553, radius_km=10)
    assert make_discovery_cache_key(DiscoveryQuery(**common, limit=5)) != make_discovery_cache_key(
        DiscoveryQuery(**common, limit=20)
    )


def test_discovery_cache_key_separates_services_and_localities():
    base = dict(lat=12.9177, lng=77.4838, radius_km=5, limit=20)
    assert make_discovery_cache_key(DiscoveryQuery(**base, service="ac-repair", area="Kengeri")) != make_discovery_cache_key(
        DiscoveryQuery(**base, service="home-cleaning", area="Rajajinagar")
    )


def test_catalogue_resolution_falls_back_when_database_schema_is_unavailable():
    class BrokenQuery:
        def filter(self, *args, **kwargs):
            raise OperationalError("SELECT", {}, Exception("services table missing"))

    class BrokenDatabase:
        def query(self, model):
            return BrokenQuery()

        def rollback(self):
            self.rolled_back = True

    db = BrokenDatabase()
    resolved = CatalogueResolver.resolve("split-ac-regular-service", db=db)

    assert resolved.service_slug == "split-ac-regular-service"
    assert resolved.category_slug == "ac-repair"
    assert db.rolled_back is True
