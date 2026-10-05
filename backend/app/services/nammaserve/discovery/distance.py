import math
from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in kilometers between two points on the Earth (WGS84)."""
    # Earth radius in kilometers
    earth_radius_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(earth_radius_km * c, 2)


def haversine_sql_expression(
    user_lat: float,
    user_lng: float,
    lat_col: ColumnElement,
    lng_col: ColumnElement,
) -> ColumnElement:
    """Generate a database-side SQL expression for Haversine distance in kilometers.

    Compatible with standard SQL / PostgreSQL / SQLite.
    """
    earth_radius_km = 6371.0
    rad_user_lat = math.radians(user_lat)
    rad_user_lng = math.radians(user_lng)

    # Convert table degrees to radians
    rad_lat = func.radians(lat_col)
    rad_lng = func.radians(lng_col)

    # Spherical Law of Cosines or Haversine formula
    return earth_radius_km * func.acos(
        func.least(
            1.0,
            func.greatest(
                -1.0,
                func.sin(rad_user_lat) * func.sin(rad_lat)
                + func.cos(rad_user_lat) * func.cos(rad_lat) * func.cos(rad_lng - rad_user_lng),
            ),
        )
    )
