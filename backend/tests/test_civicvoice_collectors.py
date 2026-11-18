from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest

from app.schemas.civicvoice import NormalizedSourceRecord
from app.services.civicvoice.collectors.base import (
    CollectorAuthError,
    CollectorError,
    CollectorNetworkError,
    CollectorQuotaError,
    compute_dedup_key,
    parse_iso_datetime,
)
from app.services.civicvoice.collectors.bluesky import BlueskyCollector
from app.services.civicvoice.collectors.tavily import TavilyCollector
from app.services.civicvoice.collectors.youtube import YouTubeCollector


# ============================================================================
# Helpers & Utilities Tests
# ============================================================================


def test_compute_dedup_key_deterministic():
    key1 = compute_dedup_key("youtube", "vid123", "https://youtube.com/watch?v=vid123")
    key2 = compute_dedup_key("youtube", "vid123", "https://different.url")
    assert key1 == key2
    assert len(key1) == 64

    url_key1 = compute_dedup_key("tavily", None, "https://example.com/page1")
    url_key2 = compute_dedup_key("tavily", "", "HTTPS://EXAMPLE.COM/page1")
    assert url_key1 == url_key2
    assert len(url_key1) == 64


def test_parse_iso_datetime():
    dt = parse_iso_datetime("2024-10-25T14:30:00.000Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2024

    assert parse_iso_datetime(None) is None
    assert parse_iso_datetime("not-a-date") is None


# ============================================================================
# Bluesky Collector Tests
# ============================================================================


@pytest.mark.anyio
async def test_bluesky_success_english_and_kannada():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    kannada_text = "ಬೆಂಗಳೂರಿನ ರಸ್ತೆಗಳಲ್ಲಿ ಗುಂಡಿಗಳು ಹೆಚ್ಚಾಗಿವೆ #SpotFix"

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.is_error = False
    mock_resp.json.return_value = {
        "posts": [
            {
                "uri": "at://did:plc:123/app.bsky.feed.post/3kn1",
                "cid": "cid1",
                "author": {
                    "handle": "citizen.bsky.social",
                    "did": "did:plc:123",
                    "displayName": "Bengaluru Citizen",
                },
                "record": {
                    "text": kannada_text,
                    "createdAt": "2024-10-25T14:30:00Z",
                    "langs": ["kn"],
                },
            }
        ]
    }
    mock_client.get.return_value = mock_resp

    collector = BlueskyCollector(client=mock_client)
    records = await collector.collect(query="ಗುಂಡಿಗಳು", limit=5, topic="roads")

    assert len(records) == 1
    rec = records[0]
    assert rec.provider == "bluesky"
    assert rec.external_id == "at://did:plc:123/app.bsky.feed.post/3kn1"
    assert rec.content == kannada_text
    assert rec.language == "kn"
    assert rec.author == "citizen.bsky.social"
    assert rec.url == "https://bsky.app/profile/citizen.bsky.social/post/3kn1"
    assert rec.topic == "roads"
    assert rec.metadata_json["author_display_name"] == "Bengaluru Citizen"


@pytest.mark.anyio
async def test_bluesky_empty_results():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.is_error = False
    mock_resp.json.return_value = {"posts": []}
    mock_client.get.return_value = mock_resp

    collector = BlueskyCollector(client=mock_client)
    records = await collector.collect(query="random non-existent query")
    assert records == []


@pytest.mark.anyio
async def test_bluesky_missing_optional_fields():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.is_error = False
    # Post missing author, record, langs, etc.
    mock_resp.json.return_value = {
        "posts": [
            {
                "uri": "at://did:plc:xyz/app.bsky.feed.post/999",
            }
        ]
    }
    mock_client.get.return_value = mock_resp

    collector = BlueskyCollector(client=mock_client)
    records = await collector.collect(query="test")
    assert len(records) == 1
    assert records[0].content is None
    assert records[0].language is None
    assert records[0].author is None
    assert records[0].published_at is None


@pytest.mark.anyio
async def test_bluesky_malformed_response():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.is_error = False
    mock_resp.json.side_effect = ValueError("Invalid JSON")
    mock_client.get.return_value = mock_resp

    collector = BlueskyCollector(client=mock_client)
    with pytest.raises(CollectorError) as exc_info:
        await collector.collect(query="test")
    assert "Malformed JSON" in str(exc_info.value)


@pytest.mark.anyio
async def test_bluesky_rate_limit_429():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 429
    mock_resp.is_error = True
    mock_client.get.return_value = mock_resp

    collector = BlueskyCollector(client=mock_client)
    with pytest.raises(CollectorQuotaError):
        await collector.collect(query="test")


@pytest.mark.anyio
async def test_bluesky_auth_error_401():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 401
    mock_resp.is_error = True
    mock_client.get.return_value = mock_resp

    collector = BlueskyCollector(client=mock_client)
    with pytest.raises(CollectorAuthError):
        await collector.collect(query="test")


@pytest.mark.anyio
async def test_bluesky_timeout_and_network_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Read timed out")

    collector = BlueskyCollector(client=mock_client)
    with pytest.raises(CollectorNetworkError):
        await collector.collect(query="test")


@pytest.mark.anyio
async def test_bluesky_in_run_deduplication():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.is_error = False
    mock_resp.json.return_value = {
        "posts": [
            {
                "uri": "at://did:plc:123/app.bsky.feed.post/dup1",
                "author": {"handle": "user.bsky.social"},
                "record": {"text": "Duplicate post 1"},
            },
            {
                "uri": "at://did:plc:123/app.bsky.feed.post/dup1",
                "author": {"handle": "user.bsky.social"},
                "record": {"text": "Duplicate post 1 repeat"},
            },
        ]
    }
    mock_client.get.return_value = mock_resp

    collector = BlueskyCollector(client=mock_client)
    records = await collector.collect(query="test", limit=10)
    assert len(records) == 1


# ============================================================================
# YouTube Collector Tests
# ============================================================================


@pytest.mark.anyio
async def test_youtube_success_parsing():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.is_error = False
    mock_resp.json.return_value = {
        "items": [
            {
                "id": {"videoId": "vid_xyz123"},
                "snippet": {
                    "publishedAt": "2024-10-20T10:00:00Z",
                    "channelId": "UC_channel_1",
                    "title": "Bengaluru Pothole Investigation",
                    "description": "On-ground report of Outer Ring Road potholes.",
                    "channelTitle": "Civic Watch",
                },
            }
        ]
    }
    mock_client.get.return_value = mock_resp

    collector = YouTubeCollector(api_key="test_dummy_key", client=mock_client)
    records = await collector.collect(query="Bengaluru potholes", limit=5)

    assert len(records) == 1
    rec = records[0]
    assert rec.provider == "youtube"
    assert rec.external_id == "vid_xyz123"
    assert rec.title == "Bengaluru Pothole Investigation"
    assert rec.content == "On-ground report of Outer Ring Road potholes."
    assert rec.url == "https://www.youtube.com/watch?v=vid_xyz123"
    assert rec.author == "Civic Watch"
    assert rec.language is None  # honest preservation
    assert rec.metadata_json["channel_id"] == "UC_channel_1"


@pytest.mark.anyio
async def test_youtube_missing_api_key():
    collector = YouTubeCollector(api_key="")
    with pytest.raises(CollectorAuthError) as exc_info:
        await collector.collect(query="test")
    assert "YouTube API key is not configured" in str(exc_info.value)


@pytest.mark.anyio
async def test_youtube_quota_403_and_rate_limit_429():
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # 403 quota
    mock_resp_403 = MagicMock(spec=httpx.Response)
    mock_resp_403.status_code = 403
    mock_resp_403.is_error = True
    mock_client.get.return_value = mock_resp_403

    collector = YouTubeCollector(api_key="test_key", client=mock_client)
    with pytest.raises(CollectorQuotaError):
        await collector.collect(query="test")

    # 429 rate limit
    mock_resp_429 = MagicMock(spec=httpx.Response)
    mock_resp_429.status_code = 429
    mock_resp_429.is_error = True
    mock_client.get.return_value = mock_resp_429
    with pytest.raises(CollectorQuotaError):
        await collector.collect(query="test")


@pytest.mark.anyio
async def test_youtube_timeout_and_network_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectTimeout("Connection timed out")

    collector = YouTubeCollector(api_key="test_key", client=mock_client)
    with pytest.raises(CollectorNetworkError):
        await collector.collect(query="test")


# ============================================================================
# Tavily Collector Tests
# ============================================================================


@pytest.mark.anyio
async def test_tavily_success_parsing():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.is_error = False
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "East Bengaluru Residents Protest Garbage Dumping",
                "url": "https://www.deccanherald.com/city/top-stories/bengaluru-garbage",
                "content": "Citizens from Mahadevapura demanded action from BBMP.",
                "score": 0.94,
                "published_date": "2024-10-18T09:30:00Z",
            }
        ]
    }
    mock_client.post.return_value = mock_resp

    collector = TavilyCollector(api_key="test_dummy_tavily", client=mock_client)
    records = await collector.collect(query="Bengaluru garbage protest", limit=5, topic="waste")

    assert len(records) == 1
    rec = records[0]
    assert rec.provider == "tavily"
    assert rec.external_id is None
    assert rec.title == "East Bengaluru Residents Protest Garbage Dumping"
    assert rec.url == "https://www.deccanherald.com/city/top-stories/bengaluru-garbage"
    assert rec.author == "www.deccanherald.com"
    assert rec.topic == "waste"
    assert rec.metadata_json["score"] == 0.94


@pytest.mark.anyio
async def test_tavily_missing_api_key():
    collector = TavilyCollector(api_key="")
    with pytest.raises(CollectorAuthError) as exc_info:
        await collector.collect(query="test")
    assert "Tavily API key is not configured" in str(exc_info.value)


@pytest.mark.anyio
async def test_tavily_auth_and_rate_limit():
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # 401
    mock_resp_401 = MagicMock(spec=httpx.Response)
    mock_resp_401.status_code = 401
    mock_resp_401.is_error = True
    mock_client.post.return_value = mock_resp_401

    collector = TavilyCollector(api_key="test_key", client=mock_client)
    with pytest.raises(CollectorAuthError):
        await collector.collect(query="test")

    # 429
    mock_resp_429 = MagicMock(spec=httpx.Response)
    mock_resp_429.status_code = 429
    mock_resp_429.is_error = True
    mock_client.post.return_value = mock_resp_429
    with pytest.raises(CollectorQuotaError):
        await collector.collect(query="test")


@pytest.mark.anyio
async def test_tavily_malformed_and_timeout():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.is_error = False
    mock_resp.json.side_effect = ValueError("Corrupt body")
    mock_client.post.return_value = mock_resp

    collector = TavilyCollector(api_key="test_key", client=mock_client)
    with pytest.raises(CollectorError):
        await collector.collect(query="test")

    mock_client.post.side_effect = httpx.ReadTimeout("Timeout")
    with pytest.raises(CollectorNetworkError):
        await collector.collect(query="test")
