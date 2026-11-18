from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models.civicvoice import CivicVoiceCitizenSubmission, CivicVoiceSourceRecord
from app.schemas.civicvoice import (
    CivicVoiceSearchRequest,
    CivicVoiceSummaryResponse,
    GeminiFindingItem,
    GeminiProblemConcernItem,
    GeminiResearchOutput,
    GeminiSuggestionItem,
    GeminiViewpointContrastItem,
    NormalizedSourceRecord,
)
from app.services.civicvoice.intelligence.evidence_preparer import (
    EvidencePreparer,
    PreparedEvidenceItem,
)
from app.services.civicvoice.intelligence.evidence_validator import EvidenceValidator
from app.services.civicvoice.intelligence.gemini_researcher import (
    CivicVoiceGeminiResearcher,
    GeminiNotConfiguredError,
    GeminiResearchError,
)
from app.services.civicvoice.service import CivicVoiceService


# ============================================================================
# Helpers and Fixtures
# ============================================================================


class FakeGeminiModels:
    def __init__(self, output_payload: dict | None = None, should_fail: bool = False, is_timeout: bool = False):
        self.output_payload = output_payload
        self.should_fail = should_fail
        self.is_timeout = is_timeout

    def generate_content(self, model: str, contents: str, config: any):
        if self.is_timeout:
            raise TimeoutError("Gemini API call timed out after 25.0 seconds.")
        if self.should_fail:
            raise RuntimeError("Gemini 500 internal quota failure.")
        if self.output_payload is not None:
            mock_resp = MagicMock()
            mock_resp.text = json.dumps(self.output_payload)
            return mock_resp
        mock_resp = MagicMock()
        mock_resp.text = "{}"
        return mock_resp


class FakeGeminiClient:
    def __init__(self, output_payload: dict | None = None, should_fail: bool = False, is_timeout: bool = False):
        self.models = FakeGeminiModels(output_payload=output_payload, should_fail=should_fail, is_timeout=is_timeout)


@pytest.fixture
def evidence_preparer():
    return EvidencePreparer()


@pytest.fixture
def evidence_validator():
    return EvidenceValidator()


# ============================================================================
# 1. Mysore Dasara 2026: Informational & Opinion-bearing Sources
# ============================================================================


def test_mysore_dasara_evidence_preparation(evidence_preparer):
    """Verifies that evidence preparer classifies official schedule info vs public commentary correctly."""
    now = datetime.now(timezone.utc)

    records = [
        NormalizedSourceRecord(
            provider="tavily",
            dedup_key="dasara_official",
            topic="Mysore Dasara 2026",
            title="Karnataka Government Announces Mysore Dasara 2026 Schedule",
            content="The 2026 Mysore Dasara festival will take place from October 11 to October 20. Official passes and jumboo savari route released.",
            url="https://mysuru.nic.in/en/events/dasara-2026",
            collected_at=now,
        ),
        NormalizedSourceRecord(
            provider="bluesky",
            dedup_key="dasara_social",
            topic="Mysore Dasara 2026",
            title="Mysore Dasara 2026 crowd feedback",
            content="Attended the Mysore Dasara 2026 illumination yesterday! Truly amazing lighting but parking was a complete nightmare and traffic jam was horrible.",
            url="https://bsky.app/profile/citizen/post/123",
            author="commuter_blr",
            collected_at=now,
        ),
    ]

    relevant, filtered = evidence_preparer.prepare_evidence("Mysore Dasara 2026", records)
    assert len(relevant) == 2
    assert len(filtered) == 0

    official_item = next(item for item in relevant if "mysuru.nic.in" in item.url)
    social_item = next(item for item in relevant if "bsky.app" in item.url)

    assert official_item.source_type == "official_information"
    assert official_item.is_opinion_bearing is False

    assert social_item.source_type == "public_opinion"
    assert social_item.is_opinion_bearing is True


# ============================================================================
# 2. Technology & Product Launch Topic
# ============================================================================


def test_technology_and_product_launch_topic(evidence_preparer):
    """Verifies technology product launch sources with tech news vs user sentiments."""
    now = datetime.now(timezone.utc)
    records = [
        NormalizedSourceRecord(
            provider="tavily",
            dedup_key="tech_launch_1",
            topic="AstraOS Launch",
            title="TechCorp Officially Launches AstraOS for Smart Bengaluru Infrastructure",
            content="TechCorp has deployed AstraOS version 3 across 50 smart junctions in Bengaluru to coordinate traffic lights.",
            url="https://thehindu.com/technology/techcorp-astraos-launch",
            collected_at=now,
        ),
        NormalizedSourceRecord(
            provider="bluesky",
            dedup_key="tech_launch_2",
            topic="AstraOS Launch",
            title="AstraOS review",
            content="I feel AstraOS is wonderful for synchronization, but we faced glitches near Marathahalli junction today.",
            url="https://bsky.app/profile/dev/post/456",
            collected_at=now,
        ),
    ]

    relevant, _ = evidence_preparer.prepare_evidence("AstraOS Launch", records)
    assert len(relevant) == 2
    assert relevant[0].publisher in ("Thehindu", "The Hindu", "Tavily")
    assert relevant[1].is_opinion_bearing is True


# ============================================================================
# 3. Irrelevant Search Results Filtering
# ============================================================================


def test_irrelevant_search_results_filtering(evidence_preparer):
    """Verifies that off-topic records are excluded prior to research synthesis."""
    now = datetime.now(timezone.utc)
    records = [
        NormalizedSourceRecord(
            provider="tavily",
            dedup_key="relevant_metro",
            topic="Bengaluru Metro Phase 2",
            title="Bengaluru Metro Phase 2 Reach 6 trial runs underway",
            content="Namma Metro conducts speed trials on the Pink Line between Kalena Agrahara and Nagawara.",
            url="https://deccanherald.com/city/bengaluru-metro-pink-line",
            collected_at=now,
        ),
        NormalizedSourceRecord(
            provider="tavily",
            dedup_key="irrelevant_item",
            topic="Bengaluru Metro Phase 2",
            title="Paris Metro introduces new automated ticketing system",
            content="The RATP in France has upgraded ticketing terminals across central Paris stations.",
            url="https://example.com/paris-transit-news",
            collected_at=now,
        ),
    ]

    relevant, filtered = evidence_preparer.prepare_evidence("Bengaluru Metro Phase 2", records)
    assert len(relevant) == 1
    assert "bengaluru-metro" in relevant[0].url
    assert len(filtered) == 1
    assert "paris-transit" in filtered[0].url


# ============================================================================
# 4. Conflicting Sources and Missing Publication Dates
# ============================================================================


def test_conflicting_sources_and_missing_publication_dates(evidence_validator):
    """Verifies that missing publication dates are flagged in limitations and viewpoints handle conflicts."""
    now = datetime.now(timezone.utc)
    item1 = PreparedEvidenceItem(
        source_id="SRC-1",
        record_id="r1",
        provider="bluesky",
        title="Pro-flyover viewpoint",
        publisher="Bluesky",
        url="https://bsky.app/post/1",
        published_at=None,  # Missing publication timestamp
        retrieved_at=now,
        excerpt="The new elevated corridor has reduced travel times by 20 minutes. Commuters are delighted.",
        source_type="public_opinion",
        is_opinion_bearing=True,
        relevance_score=0.9,
    )
    item2 = PreparedEvidenceItem(
        source_id="SRC-2",
        record_id="r2",
        provider="bluesky",
        title="Anti-flyover critique",
        publisher="Bluesky",
        url="https://bsky.app/post/2",
        published_at=None,  # Missing publication timestamp
        retrieved_at=now,
        excerpt="The elevated corridor displaced hundreds of trees and created waterlogging bottlenecks underneath.",
        source_type="public_opinion",
        is_opinion_bearing=True,
        relevance_score=0.85,
    )

    report = GeminiResearchOutput(
        topic="Elevated Corridor Debate",
        introduction="Analysis of public discourse regarding the proposed elevated road corridor in Bengaluru.",
        overall_summary="Opinions are sharply polarized between commuter travel time savings and environmental concerns.",
        positive_findings=[
            GeminiFindingItem(
                heading="Commuter Travel Time Relief",
                explanation="Commuters note significant reductions in travel times along the arterial corridor.",
                supporting_source_ids=["SRC-1"],
            )
        ],
        negative_findings=[
            GeminiFindingItem(
                heading="Ecological Impact and Waterlogging",
                explanation="Residents express distress over tree loss and drainage bottlenecks underneath the pillars.",
                supporting_source_ids=["SRC-2"],
            )
        ],
        different_viewpoints=[
            GeminiViewpointContrastItem(
                topic_aspect="Infrastructure Impact",
                areas_of_agreement="Both sides acknowledge major mobility challenges on the existing surface road.",
                points_of_disagreement="Divergence over whether concrete elevated structures outweigh environmental damage.",
                disputed_questions=["Can compensatory afforestation and modernized stormwater drainage offset corridor impacts?"],
            )
        ],
    )

    summary = evidence_validator.validate_and_assemble(
        report=report,
        evidence_items=[item1, item2],
        source_records_map={},
        ai_model_name="gemini-2.0-flash",
    )

    assert summary.coverage.missing_timestamps_count == 2
    assert any("lack explicit publication timestamps" in lim for lim in summary.coverage.limitations)
    assert len(summary.viewpoint_contrasts) == 1
    assert "Infrastructure Impact" == summary.viewpoint_contrasts[0].topic_aspect


# ============================================================================
# 5. Missing Opinions Despite Abundant Factual Information
# ============================================================================


def test_missing_opinions_honest_empty_sections(evidence_validator):
    """Verifies that purely factual/official articles are not counted as public sentiment."""
    now = datetime.now(timezone.utc)
    item1 = PreparedEvidenceItem(
        source_id="SRC-1",
        record_id="r1",
        provider="tavily",
        title="BBMP Ward Delimitation Gazetted",
        publisher="Deccan Herald",
        url="https://deccanherald.com/bbmp-ward-gazette",
        published_at=now,
        retrieved_at=now,
        excerpt="The urban development department has published the final notification revising ward boundaries to 225 wards.",
        source_type="news_reporting",
        is_opinion_bearing=False,
        relevance_score=0.9,
    )

    # Gemini output honestly returning empty list for opinions because only facts exist
    report = GeminiResearchOutput(
        topic="BBMP Ward Delimitation",
        introduction="Overview of the gazette notification regarding municipal ward delimitation.",
        overall_summary="The collected evidence consists of descriptive reporting outlining the statutory gazette notification.",
        positive_findings=[],
        negative_findings=[],
        problems_and_concerns=[],
        suggestions=[],
        different_viewpoints=[],
        unresolved_questions=["No citizen sentiment or political opposition commentary has been indexed yet."],
    )

    summary = evidence_validator.validate_and_assemble(
        report=report,
        evidence_items=[item1],
        source_records_map={},
        ai_model_name="gemini-2.0-flash",
    )

    assert summary.positive_opinions == []
    assert "No reliable positive opinions" in (summary.positive_opinions_status or "")
    assert summary.negative_opinions == []
    assert "No critical, dissatisfied, or opposing viewpoints" in (summary.negative_opinions_status or "")
    assert len(summary.unresolved_questions) == 1


# ============================================================================
# 6. Missing Evidence and Follow-up Search Behavior
# ============================================================================


@pytest.mark.anyio
async def test_gap_detection_and_followup_searches():
    """Verifies that researcher detects evidence gaps and triggers targeted follow-up queries."""
    now = datetime.now(timezone.utc)
    initial_fact = PreparedEvidenceItem(
        source_id="SRC-1",
        record_id="r1",
        provider="tavily",
        title="Flower Show 2026 dates announced",
        publisher="The Hindu",
        url="https://thehindu.com/flower-show-2026",
        published_at=now,
        retrieved_at=now,
        excerpt="The Lalbagh Republic Day Flower Show 2026 will run for 10 days.",
        source_type="news_reporting",
        is_opinion_bearing=False,
        relevance_score=0.9,
    )

    # Followup collector mock returning a citizen complaint
    followup_called_with = []

    async def mock_followup(query: str, limit: int) -> list[PreparedEvidenceItem]:
        followup_called_with.append(query)
        return [
            PreparedEvidenceItem(
                source_id="TEMP-1",
                record_id="r2",
                provider="bluesky",
                title="Lalbagh Flower Show crowd complaints",
                publisher="Bluesky",
                url="https://bsky.app/post/flower-show-crowds",
                published_at=now,
                retrieved_at=now,
                excerpt="Ticket queues were massive today at Lalbagh West Gate, took 45 mins just to enter.",
                source_type="public_opinion",
                is_opinion_bearing=True,
                relevance_score=0.85,
            )
        ]

    output_payload = {
        "topic": "Lalbagh Flower Show 2026",
        "introduction": "The annual Lalbagh Flower Show 2026 attracts thousands of visitors to South Bengaluru.",
        "overall_summary": "While the exhibition remains widely cherished, visitors experienced substantial gate entry delays.",
        "positive_findings": [],
        "negative_findings": [
            {
                "heading": "Gate Entry and Ticketing Delays",
                "explanation": "Visitors reported 45-minute ticketing queues at West Gate.",
                "supporting_source_ids": ["SRC-2"],
                "evidence_strength": "moderate",
            }
        ],
        "problems_and_concerns": [],
        "suggestions": [],
        "different_viewpoints": [],
        "trends_overview": "Steady seasonal interest.",
        "trends_available": False,
        "unresolved_questions": [],
        "limitations": [],
        "follow_up_queries_suggested": [],
    }

    researcher = CivicVoiceGeminiResearcher(
        client=FakeGeminiClient(output_payload=output_payload),
        model="gemini-2.0-flash",
    )

    report, final_evidence = await researcher.execute_research(
        query="Lalbagh Flower Show 2026",
        initial_evidence=[initial_fact],
        followup_collector=mock_followup,
        max_followup_rounds=1,
    )

    assert len(followup_called_with) == 1
    assert "public reactions" in followup_called_with[0]
    assert len(final_evidence) == 2
    assert final_evidence[1].source_id == "SRC-2"
    assert len(report.negative_findings) == 1


# ============================================================================
# 7. Gemini Timeouts and Invalid Output Handling
# ============================================================================


@pytest.mark.anyio
async def test_gemini_timeout_handling():
    """Verifies that Gemini API timeouts raise GeminiResearchError safely."""
    now = datetime.now(timezone.utc)
    item = PreparedEvidenceItem(
        source_id="SRC-1",
        record_id="r1",
        provider="bluesky",
        title="Sample",
        publisher="Bluesky",
        url="https://example.com/1",
        published_at=now,
        retrieved_at=now,
        excerpt="Sample excerpt.",
        source_type="public_opinion",
        is_opinion_bearing=True,
        relevance_score=0.8,
    )

    researcher = CivicVoiceGeminiResearcher(
        client=FakeGeminiClient(is_timeout=True),
        model="gemini-2.0-flash",
    )

    with pytest.raises(GeminiResearchError) as exc_info:
        await researcher.execute_research("Test Query", [item])

    assert "timed out" in str(exc_info.value).lower()


# ============================================================================
# 8. Unsupported Source IDs & Invented Numerical Claims (Validation)
# ============================================================================


def test_validator_strips_unsupported_source_ids_and_flags_numbers(evidence_validator):
    """Verifies that application-side validator strips hallucinated source IDs and catches invented numbers."""
    now = datetime.now(timezone.utc)
    real_evidence = PreparedEvidenceItem(
        source_id="SRC-1",
        record_id="r1",
        provider="bluesky",
        title="Pothole complaint",
        publisher="Bluesky",
        url="https://bsky.app/pothole/1",
        published_at=now,
        retrieved_at=now,
        excerpt="Huge potholes on 100 Feet Road Indiranagar causing severe vehicle damage.",
        source_type="public_opinion",
        is_opinion_bearing=True,
        relevance_score=0.9,
    )

    # Gemini attempts to cite non-existent SRC-99 and invent a 400% claim
    report = GeminiResearchOutput(
        topic="Indiranagar Potholes",
        introduction="Road conditions in Indiranagar.",
        overall_summary="Potholes have reportedly increased by 400% this quarter causing unanimous citizen rage.",
        positive_findings=[],
        negative_findings=[
            GeminiFindingItem(
                heading="Potholes on 100 Feet Road",
                explanation="Vehicle owners face damages on 100 Feet Road.",
                supporting_source_ids=["SRC-1", "SRC-99"],  # SRC-99 is hallucinated
            ),
            GeminiFindingItem(
                heading="Invented Finding With No Valid Source",
                explanation="Claims that ₹50,000 in repair funds was misused.",
                supporting_source_ids=["SRC-88"],  # Completely invalid citation
            ),
        ],
        problems_and_concerns=[
            GeminiProblemConcernItem(
                heading="Invented Problem",
                description="Invented description with bad source.",
                supporting_source_ids=["SRC-77"],
            )
        ],
        suggestions=[
            GeminiSuggestionItem(
                heading="Repair road",
                suggestion="Pave 100 Feet Road.",
                origin="source_author",
                supporting_source_ids=["SRC-99"],  # Invalid citation for author suggestion
            )
        ],
        different_viewpoints=[],
    )

    summary = evidence_validator.validate_and_assemble(
        report=report,
        evidence_items=[real_evidence],
        source_records_map={},
        ai_model_name="gemini-2.0-flash",
    )

    # 1. SRC-99 was stripped from the first finding, leaving only SRC-1
    assert len(summary.negative_opinions) == 1
    assert summary.negative_opinions[0].heading == "Potholes on 100 Feet Road"
    assert summary.negative_opinions[0].evidence_record_ids == ["r1"]

    # 2. Second finding had zero valid citations -> suppressed
    assert not any(f.heading == "Invented Finding With No Valid Source" for f in summary.negative_opinions)

    # 3. Problem with only invalid source was suppressed
    assert len(summary.problems_and_concerns) == 0

    # 4. Suggestion claiming source_author with invalid citation was safely converted to synthesized_civicvoice
    assert len(summary.suggestions_and_improvements) == 1
    assert summary.suggestions_and_improvements[0].origin == "synthesized_civicvoice"

    # 5. Broad consensus language in summary was softened for small sample
    assert "unanimous" not in summary.overall_summary.lower()

    # 6. Validation status reflects corrections
    assert summary.validation_status == "validated_with_corrections"
    assert len(summary.validation_notes) >= 3


# ============================================================================
# 9. Empty Searches and Complete Provider Failure Handling
# ============================================================================


def test_empty_search_and_provider_failure(test_client_and_db):
    """Verifies that empty searches return honest empty structured response without error."""
    client, session = test_client_and_db

    # Mock collectors returning empty
    with patch("app.api.v1.endpoints.civicvoice.civicvoice_service.bluesky.collect", new_callable=AsyncMock) as m_b, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.youtube.collect", new_callable=AsyncMock) as m_y, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.tavily.collect", new_callable=AsyncMock) as m_t:
        m_b.return_value = []
        m_y.return_value = []
        m_t.return_value = []

        resp = client.post(
            "/api/v1/civicvoice/search",
            json={"query": "XyzNonExistentTopic98765", "limit_per_provider": 5},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_records"] == 0
        summary = data["summary"]
        assert summary["positive_opinions"] == []
        assert summary["negative_opinions"] == []
        assert "zero" in summary["sample_size_assessment"].lower() or "no records" in summary["sample_size_assessment"].lower()


# ============================================================================
# 10. Citizen Privacy Isolation
# ============================================================================


def test_citizen_privacy_isolation_in_search(test_client_and_db):
    """Verifies that private citizen submissions are NEVER leaked through the public search endpoint."""
    client, session = test_client_and_db
    now = datetime.now(timezone.utc)

    # Insert a private citizen submission
    private_sub = CivicVoiceCitizenSubmission(
        id="priv-sub-1234",
        topic="Mysore Dasara 2026",
        opinion_text="SECRET_PRIVATE_CITIZEN_OPINION: My phone is 9988776655 and my secret home address is Indiranagar 5th Main.",
        locality="Indiranagar",
        language="en",
        consent_given=True,
        created_at=now,
    )
    session.add(private_sub)
    session.commit()

    with patch("app.api.v1.endpoints.civicvoice.civicvoice_service.bluesky.collect", new_callable=AsyncMock) as m_b, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.youtube.collect", new_callable=AsyncMock) as m_y, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.tavily.collect", new_callable=AsyncMock) as m_t:
        m_b.return_value = []
        m_y.return_value = []
        m_t.return_value = []

        resp = client.post(
            "/api/v1/civicvoice/search",
            json={"query": "Mysore Dasara 2026", "limit_per_provider": 5},
        )
        assert resp.status_code == 200
        raw_response_text = resp.text

        # Verify that raw private text, phone number, and ID never appear anywhere in the response
        assert "SECRET_PRIVATE_CITIZEN_OPINION" not in raw_response_text
        assert "9988776655" not in raw_response_text
        assert "priv-sub-1234" not in raw_response_text

        data = resp.json()
        assert data["citizen_submissions_count"] >= 1  # Volume count aggregate is reported safely


# ============================================================================
# 11. Unconfigured Gemini Graceful Fallback
# ============================================================================


def test_unconfigured_gemini_graceful_fallback(test_client_and_db, monkeypatch):
    """Verifies that when Gemini is not configured, search returns transparent rule-based fallback without breaking."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", None)
    client, session = test_client_and_db
    now = datetime.now(timezone.utc)

    # Pre-seed a record
    rec = CivicVoiceSourceRecord(
        id="rec-fallback-1",
        provider="tavily",
        dedup_key="fallback_dedup",
        topic="Water Pipeline Leak",
        title="Water pipeline burst on Outer Ring Road",
        content="Water leakage reported on Outer Ring Road near Bellandur causing water supply disruption and traffic delay.",
        url="https://example.com/leak/1",
        collected_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.commit()

    with patch("app.api.v1.endpoints.civicvoice.civicvoice_service.bluesky.collect", new_callable=AsyncMock) as m_b, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.youtube.collect", new_callable=AsyncMock) as m_y, \
         patch("app.api.v1.endpoints.civicvoice.civicvoice_service.tavily.collect", new_callable=AsyncMock) as m_t:
        m_b.return_value = []
        m_y.return_value = []
        m_t.return_value = []

        resp = client.post(
            "/api/v1/civicvoice/search",
            json={"query": "Water Pipeline Leak", "limit_per_provider": 5},
        )
        assert resp.status_code == 200
        data = resp.json()

    summary = data["summary"]
    assert summary["ai_synthesized"] is False
    assert summary["validation_status"] == "rule_based_fallback"
    assert any("Gemini API key is not configured" in note for note in summary["validation_notes"])
