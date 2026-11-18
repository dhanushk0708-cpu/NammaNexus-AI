import re
import urllib.parse
from typing import Tuple


GOOGLE_MAPS_DOMAINS = {
    "maps.google.com",
    "www.google.com",
    "google.com",
    "maps.app.goo.gl",
    "goo.gl",
}


def is_valid_google_maps_url(url: str) -> bool:
    """Validates whether a URL is a legitimate Google Maps web or share link."""
    if not url or not isinstance(url, str):
        return False

    cleaned = url.strip()
    if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
        return False

    try:
        parsed = urllib.parse.urlparse(cleaned)
        netloc = parsed.netloc.lower()
        # Remove port if present
        if ":" in netloc:
            netloc = netloc.split(":")[0]

        # Check domain
        if netloc in GOOGLE_MAPS_DOMAINS:
            if netloc in {"www.google.com", "google.com"} and not parsed.path.startswith("/maps"):
                return False
            return True

        if netloc.endswith(".google.com") and parsed.path.startswith("/maps"):
            return True

        return False
    except Exception:
        return False


def extract_coordinates_from_maps_url(url: str) -> Tuple[float | None, float | None]:
    """Deterministically extracts latitude and longitude from common Google Maps URL patterns.

    Supported patterns:
    - @12.9345,77.6241
    - ?q=12.9345,77.6241
    - ?ll=12.9345,77.6241
    - !3d12.9345!4d77.6241
    """
    if not is_valid_google_maps_url(url):
        return None, None

    # Pattern 1: @lat,lng (e.g. /@12.9716,77.6412,15z)
    at_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if at_match:
        lat, lng = float(at_match.group(1)), float(at_match.group(2))
        if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
            return lat, lng

    # Pattern 2: ?q=lat,lng or &q=lat,lng
    q_match = re.search(r"[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if q_match:
        lat, lng = float(q_match.group(1)), float(q_match.group(2))
        if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
            return lat, lng

    # Pattern 3: ?ll=lat,lng
    ll_match = re.search(r"[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if ll_match:
        lat, lng = float(ll_match.group(1)), float(ll_match.group(2))
        if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
            return lat, lng

    # Pattern 4: Protobuf data !3dlat!4dlng
    proto_match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
    if proto_match:
        lat, lng = float(proto_match.group(1)), float(proto_match.group(2))
        if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
            return lat, lng

    return None, None


def build_view_store_url(
    google_maps_url: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    address: str | None = None,
    city: str | None = "Bengaluru",
) -> str | None:
    """Builds a verified public URL for citizens to navigate to the physical store."""
    if google_maps_url and is_valid_google_maps_url(google_maps_url):
        return google_maps_url.strip()

    if latitude is not None and longitude is not None:
        return f"https://www.google.com/maps?q={latitude},{longitude}"

    if address:
        full_query = f"{address}, {city}" if city and city not in address else address
        return f"https://www.google.com/maps?q={urllib.parse.quote(full_query)}"

    return None
