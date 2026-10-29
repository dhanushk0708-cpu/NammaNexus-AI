import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.nammaserve import ReviewSummaryRequest
from app.services.nammaserve.ai.assistant import ServiceAssistant
from app.services.nammaserve.ai.review_summary import ReviewSummaryService, validate_review_url


def test_fallback_parser_handles_english_and_kannada_transliteration():
    assistant = ServiceAssistant(db=MagicMock())

    english = assistant._fallback_parse_intent("I need an AC mechanic in Rajajinagar")
    kannada = assistant._fallback_parse_intent("Nange mane clean madakke obru beku in Rajajinagara")

    assert english.service == "ac-repair"
    assert english.location == "Rajajinagar"
    assert kannada.service == "full-home-deep-cleaning-1bhk"
    assert kannada.location == "Rajajinagar"


def test_review_url_validation_rejects_non_google_and_private_destinations():
    with pytest.raises(ValueError):
        validate_review_url("https://example.com/reviews")
    with pytest.raises(ValueError):
        validate_review_url("http://127.0.0.1/maps")


def test_review_link_does_not_claim_accessible_reviews():
    request = ReviewSummaryRequest(review_url="https://maps.google.com/maps/place/example")
    response = asyncio.run(ReviewSummaryService().summarize(request))

    assert response.summary is None
    assert response.generated_by == "not-generated"
    assert "not fetched" in response.limitations[0]


def test_review_text_has_deterministic_fallback_when_ai_unavailable():
    manager = MagicMock()
    manager.run_with_fallback = AsyncMock(side_effect=RuntimeError("provider unavailable"))
    request = ReviewSummaryRequest(
        review_text="Fast service and polite staff. The waiting time was long."
    )

    response = asyncio.run(ReviewSummaryService(manager).summarize(request))

    assert response.used_user_text is True
    assert response.generated_by == "deterministic"
    assert "Fast service" in response.summary
    assert "waiting time" in response.summary
