from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.civicvoice import CivicVoiceAnalysisRecord, CivicVoiceSourceRecord
from app.schemas.civicvoice import (
    ContentIntent,
    OpinionCategory,
    SentimentLabel,
)
from app.services.civicvoice.intelligence import (
    RuleBasedMultilingualAnalyzer,
    SummarySynthesizer,
    ThemeClusterEngine,
    TrendAnalysisEngine,
    classify_theme_for_text,
    detect_text_language,
)
from app.services.civicvoice.service import CivicVoiceService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sqlite_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client_and_db(sqlite_db):
    def override_get_db():
        try:
            yield sqlite_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, sqlite_db
    app.dependency_overrides.clear()


# ============================================================================
# 1. Language Detection Tests
# ============================================================================


def test_detect_text_language():
    assert detect_text_language("Pothole problem in Koramangala") == "en"
    assert detect_text_language("ಬೆಂಗಳೂರಿನ ರಸ್ತೆಗಳಲ್ಲಿ ಗುಂಡಿಗಳು") == "kn"
    assert detect_text_language("Heavy traffic at ಸಿಲ್ಕ್ ಬೋರ್ಡ್ ಜಂಕ್ಷನ್") == "mixed"
    assert detect_text_language("") == "unknown"
    assert detect_text_language(None) == "unknown"


# ============================================================================
# 2. Multilingual Classification & Intent Tests (English & Kannada)
# ============================================================================


def test_classify_english_complaint():
    analyzer = RuleBasedMultilingualAnalyzer()
    rec = CivicVoiceSourceRecord(
        id="s1",
        provider="bluesky",
        dedup_key="d1",
        url="https://bsky.app/1",
        title="Sarjapur Road Issue",
        content="Deep potholes near the supermarket are causing daily accidents. I fell down yesterday.",
    )
    res = analyzer.analyze_record(rec)

    assert res.category == OpinionCategory.COMPLAINT_OR_CONCERN
    assert res.sentiment == SentimentLabel.NEGATIVE
    assert res.content_intent == ContentIntent.FIRST_PERSON_EXPERIENCE
    assert res.has_complaint is True
    assert "potholes" in (res.extracted_complaint or "").lower()
    assert res.confidence == "high"


def test_classify_english_positive_experience():
    analyzer = RuleBasedMultilingualAnalyzer()
    rec = CivicVoiceSourceRecord(
        id="s2",
        provider="bluesky",
        dedup_key="d2",
        url="https://bsky.app/2",
        title=None,
        content="Thank you BBMP workers! The street light on 14th cross was fixed quickly. Great work!",
    )
    res = analyzer.analyze_record(rec)

    assert res.category == OpinionCategory.POSITIVE_EXPERIENCE
    assert res.sentiment == SentimentLabel.POSITIVE
    assert res.has_complaint is False


def test_classify_english_suggestion():
    analyzer = RuleBasedMultilingualAnalyzer()
    rec = CivicVoiceSourceRecord(
        id="s3",
        provider="tavily",
        dedup_key="d3",
        url="https://news.com/3",
        title="Transit Suggestions",
        content="Please add more feeder buses from Silk Board to HSR layout. We need to improve bus connectivity.",
    )
    res = analyzer.analyze_record(rec)

    assert res.category == OpinionCategory.SUGGESTION_OR_RECOMMENDATION
    assert res.has_suggestion is True
    assert "add more feeder buses" in (res.extracted_suggestion or "").lower()


def test_classify_english_news_reporting():
    analyzer = RuleBasedMultilingualAnalyzer()
    rec = CivicVoiceSourceRecord(
        id="s4",
        provider="tavily",
        dedup_key="d4",
        url="https://news.com/4",
        title="Metro Update",
        content="According to BBMP officials, the new flyover work will commence next Monday.",
    )
    res = analyzer.analyze_record(rec)

    assert res.content_intent == ContentIntent.NEWS_OR_REPORTING
    # News announcement is not personal first-person opinion
    assert res.content_intent != ContentIntent.FIRST_PERSON_EXPERIENCE


def test_classify_english_promotional():
    analyzer = RuleBasedMultilingualAnalyzer()
    rec = CivicVoiceSourceRecord(
        id="s5",
        provider="youtube",
        dedup_key="d5",
        url="https://youtube.com/5",
        title="Car detailing offer",
        content="Special 50% discount on ceramic coating today! Call us for best price.",
    )
    res = analyzer.analyze_record(rec)

    assert res.content_intent == ContentIntent.PROMOTIONAL_MATERIAL
    assert res.category == OpinionCategory.NEUTRAL_OR_INFORMATIONAL


def test_classify_kannada_complaint():
    analyzer = RuleBasedMultilingualAnalyzer()
    rec = CivicVoiceSourceRecord(
        id="s6",
        provider="bluesky",
        dedup_key="d6",
        url="https://bsky.app/6",
        title="ಕಸದ ಸಮಸ್ಯೆ",
        content="ನಮ್ಮ ಬಡಾವಣೆಯಲ್ಲಿ ಕಸದ ಸಮಸ್ಯೆ ಹೆಚ್ಚಾಗಿದೆ, ಕೆಟ್ಟ ವಾಸನೆ ಬರುತ್ತಿದೆ.",
    )
    res = analyzer.analyze_record(rec)

    assert res.detected_language in ("kn", "mixed")
    assert res.category == OpinionCategory.COMPLAINT_OR_CONCERN
    assert res.sentiment == SentimentLabel.NEGATIVE
    assert res.has_complaint is True
    assert "ಕಸ" in (res.extracted_complaint or "")


def test_classify_kannada_positive_and_suggestion():
    analyzer = RuleBasedMultilingualAnalyzer()
    # Positive
    rec_pos = CivicVoiceSourceRecord(
        id="s7",
        provider="bluesky",
        dedup_key="d7",
        url="https://bsky.app/7",
        content="ರಸ್ತೆ ದುರಸ್ತಿ ಕಾರ್ಯ ಚೆನ್ನಾಗಿದೆ, ಧನ್ಯವಾದಗಳು ಬಿಬಿಎಂಪಿ.",
    )
    res_pos = analyzer.analyze_record(rec_pos)
    assert res_pos.category == OpinionCategory.POSITIVE_EXPERIENCE
    assert res_pos.sentiment == SentimentLabel.POSITIVE

    # Suggestion
    rec_sug = CivicVoiceSourceRecord(
        id="s8",
        provider="bluesky",
        dedup_key="d8",
        url="https://bsky.app/8",
        content="ದಯವಿಟ್ಟು ಬೆಳಗ್ಗೆ ಹೆಚ್ಚಿನ ಬಸ್ಸುಗಳನ್ನು ಒದಗಿಸಿ, ಮೆಟ್ರೋ ನಿಲ್ದಾಣಕ್ಕೆ ಅಗತ್ಯವಿದೆ.",
    )
    res_sug = analyzer.analyze_record(rec_sug)
    assert res_sug.category == OpinionCategory.SUGGESTION_OR_RECOMMENDATION
    assert res_sug.has_suggestion is True


def test_classify_insufficient_text():
    analyzer = RuleBasedMultilingualAnalyzer()
    rec = CivicVoiceSourceRecord(id="s9", provider="bluesky", dedup_key="d9", url="https://bsky.app/9", content="ok")
    res = analyzer.analyze_record(rec)
    assert res.category == OpinionCategory.UNCLEAR_OR_INSUFFICIENT
    assert res.confidence == "uncertain"


# ============================================================================
# 3. Theme Detection Tests
# ============================================================================


def test_theme_classification():
    t_id, t_label = classify_theme_for_text("Severe potholes on Outer Ring Road")
    assert t_id == "road_infrastructure"
    assert "Road Infrastructure" in t_label

    t_id2, _ = classify_theme_for_text("Garbage dumping and waste burning at night")
    assert t_id2 == "waste_management"

    t_id3, _ = classify_theme_for_text("ನೀರು ಸರಬರಾಜು ಸ್ಥಗಿತಗೊಂಡಿದೆ, ಚರಂಡಿ ತುಂಬಿದೆ")
    assert t_id3 == "water_drainage"


def test_theme_clustering_aggregates_genuine_counts():
    engine = ThemeClusterEngine()
    now = datetime.now(timezone.utc)

    s1 = CivicVoiceSourceRecord(id="src-1", provider="bluesky", dedup_key="d1", url="https://bsky.app/1", published_at=now)
    s2 = CivicVoiceSourceRecord(id="src-2", provider="youtube", dedup_key="d2", url="https://youtube.com/2", published_at=now)
    source_map = {"src-1": s1, "src-2": s2}

    a1 = CivicVoiceAnalysisRecord(
        id="a1",
        source_record_id="src-1",
        category="complaint_or_concern",
        sentiment="negative",
        theme_id="road_infrastructure",
        theme_label="Road Infrastructure & Potholes",
    )
    a2 = CivicVoiceAnalysisRecord(
        id="a2",
        source_record_id="src-2",
        category="complaint_or_concern",
        sentiment="negative",
        theme_id="road_infrastructure",
        theme_label="Road Infrastructure & Potholes",
    )

    themes = engine.cluster_records([a1, a2], source_map)
    assert len(themes) == 1
    assert themes[0].theme_id == "road_infrastructure"
    assert themes[0].record_count == 2
    assert "src-1" in themes[0].evidence_record_ids
    assert "src-2" in themes[0].evidence_record_ids
    assert len(themes[0].source_links) == 2


# ============================================================================
# 4. Trend Analysis Engine Tests
# ============================================================================


def test_trend_calculation_equivalent_windows():
    engine = TrendAnalysisEngine()
    now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)

    # 1 record in current window (Oct 13 - Oct 20)
    # 0 in previous window (Oct 06 - Oct 13)
    s1 = CivicVoiceSourceRecord(
        id="s1",
        provider="bluesky",
        dedup_key="d1",
        url="https://bsky.app/1",
        published_at=datetime(2026, 10, 18, tzinfo=timezone.utc),
    )
    source_map = {"s1": s1}

    a1 = CivicVoiceAnalysisRecord(
        id="a1",
        source_record_id="s1",
        category="complaint_or_concern",
        theme_id="traffic_congestion",
        theme_label="Traffic & Congestion Management",
    )

    trends_resp = engine.calculate_trends([a1], source_map, window_days=7, as_of_time=now)
    assert trends_resp.window_days == 7
    assert len(trends_resp.trends) == 1
    t = trends_resp.trends[0]
    assert t.current_window_count == 1
    assert t.previous_window_count == 0
    assert t.change_count == 1
    assert t.status == "single_observation"
    assert len(trends_resp.data_limitations) > 0


# ============================================================================
# 5. Evidence-Backed Summary Tests
# ============================================================================


def test_summary_synthesizer_evidence_traceability():
    synthesizer = SummarySynthesizer()
    now = datetime.now(timezone.utc)

    s1 = CivicVoiceSourceRecord(
        id="src-10",
        provider="bluesky",
        dedup_key="d10",
        url="https://bsky.app/10",
        published_at=now,
    )
    source_map = {"src-10": s1}

    a1 = CivicVoiceAnalysisRecord(
        id="a10",
        source_record_id="src-10",
        category="complaint_or_concern",
        sentiment="negative",
        theme_id="road_infrastructure",
        theme_label="Road Infrastructure & Potholes",
        has_complaint=True,
        extracted_complaint="Dangerous pothole",
        has_suggestion=True,
        extracted_suggestion="Please fill with cold mix immediately",
    )

    summary_resp = synthesizer.generate_summary([a1], source_map, topic="roads")
    assert summary_resp.coverage.total_analyzed_records == 1
    assert len(summary_resp.findings) == 1
    finding = summary_resp.findings[0]
    assert finding.supporting_record_count == 1
    assert "src-10" in finding.evidence_record_ids
    assert "https://bsky.app/10" in finding.source_urls

    assert len(summary_resp.extracted_suggestions) == 1
    assert summary_resp.extracted_suggestions[0].suggestion == "Please fill with cold mix immediately"
    assert summary_resp.extracted_suggestions[0].source_record_id == "src-10"


# ============================================================================
# 6. Database Persistence & Service Integration Tests
# ============================================================================


def test_service_analyze_and_persistence(sqlite_db):
    service = CivicVoiceService()
    now = datetime.now(timezone.utc)

    # Insert a source record
    s_rec = CivicVoiceSourceRecord(
        id="src-test-1",
        provider="bluesky",
        dedup_key="dedup-test-1",
        topic="roads",
        title="Broken road in HSR",
        content="Big pothole near BDA complex. Please repair soon.",
        url="https://bsky.app/test/1",
        collected_at=now,
        created_at=now,
        updated_at=now,
    )
    sqlite_db.add(s_rec)
    sqlite_db.commit()

    # Analyze
    analyze_resp = service.analyze_source_records(sqlite_db, topic="roads", limit=10)
    assert analyze_resp.total_examined == 1
    assert analyze_resp.total_analyzed == 1
    assert len(analyze_resp.analyses) == 1

    analysis = analyze_resp.analyses[0]
    assert analysis.source_record_id == "src-test-1"
    assert analysis.has_complaint is True
    assert analysis.has_suggestion is True
    assert analysis.theme_id == "road_infrastructure"

    # Verify saved in DB
    db_row = sqlite_db.query(CivicVoiceAnalysisRecord).filter_by(source_record_id="src-test-1").first()
    assert db_row is not None
    assert db_row.category == "complaint_or_concern"
    orig_analysis_id = db_row.id

    # Rerun with force_reanalyze=False (should skip and NOT create duplicate rows)
    rerun_resp = service.analyze_source_records(sqlite_db, topic="roads", limit=10, force_reanalyze=False)
    assert rerun_resp.total_examined == 1
    assert rerun_resp.total_analyzed == 0
    assert rerun_resp.total_skipped == 1
    all_rows = sqlite_db.query(CivicVoiceAnalysisRecord).filter_by(source_record_id="src-test-1").all()
    assert len(all_rows) == 1
    assert all_rows[0].id == orig_analysis_id

    # Rerun with force_reanalyze=True (should update in place and NOT create duplicate rows)
    force_resp = service.analyze_source_records(sqlite_db, topic="roads", limit=10, force_reanalyze=True)
    assert force_resp.total_examined == 1
    assert force_resp.total_analyzed == 1
    assert force_resp.total_skipped == 0
    all_rows_after_force = sqlite_db.query(CivicVoiceAnalysisRecord).filter_by(source_record_id="src-test-1").all()
    assert len(all_rows_after_force) == 1
    assert all_rows_after_force[0].id == orig_analysis_id



# ============================================================================
# 7. API Endpoints Tests
# ============================================================================


def test_api_analyze_unauthorized_rejected(test_client_and_db):
    client, _ = test_client_and_db
    resp = client.post("/api/v1/civicvoice/analyze", json={"topic": "roads", "limit": 10})
    assert resp.status_code == 401


def test_api_analyze_authorized_succeeds(test_client_and_db, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "civicvoice_api_token", "test-secret")
    client, db = test_client_and_db
    now = datetime.now(timezone.utc)

    # Insert a source record
    s_rec = CivicVoiceSourceRecord(
        id="src-api-1",
        provider="bluesky",
        dedup_key="dedup-api-1",
        topic="traffic",
        title="Traffic jam",
        content="Stuck in Silk Board traffic for 45 minutes.",
        url="https://bsky.app/test/api1",
        collected_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(s_rec)
    db.commit()

    headers = {"Authorization": "Bearer test-secret"}
    resp = client.post(
        "/api/v1/civicvoice/analyze",
        json={"topic": "traffic", "limit": 10},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_examined"] == 1
    assert data["total_analyzed"] == 1


def test_api_themes_and_summary_endpoints(test_client_and_db, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "civicvoice_api_token", "test-secret")
    client, db = test_client_and_db
    now = datetime.now(timezone.utc)

    # Source & Analysis records
    s_rec = CivicVoiceSourceRecord(
        id="src-api-2",
        provider="youtube",
        dedup_key="dedup-api-2",
        topic="garbage",
        title="Waste issue",
        content="Overflowing garbage bins in Indiranagar. Stench is terrible.",
        url="https://youtube.com/watch?v=api2",
        published_at=now,
        collected_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(s_rec)
    db.commit()

    # Run analyze
    client.post(
        "/api/v1/civicvoice/analyze",
        json={"topic": "garbage"},
        headers={"Authorization": "Bearer test-secret"},
    )

    # Test GET /themes
    resp_themes = client.get("/api/v1/civicvoice/themes")
    assert resp_themes.status_code == 200
    themes_data = resp_themes.json()
    assert themes_data["total_records_represented"] >= 1
    assert len(themes_data["themes"]) >= 1

    # Test GET /trends
    resp_trends = client.get("/api/v1/civicvoice/trends?window_days=7")
    assert resp_trends.status_code == 200
    trends_data = resp_trends.json()
    assert trends_data["window_days"] == 7
    assert len(trends_data["trends"]) >= 1

    # Test GET /summary
    resp_sum = client.get("/api/v1/civicvoice/summary?topic=garbage")
    assert resp_sum.status_code == 200
    sum_data = resp_sum.json()
    assert len(sum_data["findings"]) >= 1
    assert sum_data["findings"][0]["supporting_record_count"] >= 1
    assert sum_data["coverage"]["total_analyzed_records"] >= 1
    # Universal schema assertions on API response
    assert sum_data["topic_title"] == "Garbage"
    assert "Garbage" in sum_data["introduction"]
    assert len(sum_data["overall_summary"]) > 20
    assert len(sum_data["clean_sources"]) >= 1
    assert sum_data["clean_sources"][0]["publisher"] != ""


# ============================================================================
# 8. Universal Report Schema & Multi-Topic Adaptability Tests (Sections A-J)
# ============================================================================


def test_universal_report_schema_sections_a_through_j_mysore_dasara():
    """Validates that a festival search (Mysore Dasara 2026) produces all 10 universal sections A through J."""
    synthesizer = SummarySynthesizer()
    now = datetime.now(timezone.utc)

    # 3 mock sources: 1 news, 1 youtube positive, 1 bluesky complaint
    s1 = CivicVoiceSourceRecord(
        id="md-1",
        provider="tavily",
        url="https://www.deccanherald.com/mysore-dasara-2026-schedule",
        author="www.deccanherald.com",
        title="Mysore Dasara 2026 Schedule and Gold Howdah Preparations Announced",
        content="The state government has announced initial arrangements for Mysore Dasara 2026 with enhanced lighting and cultural events.",
        published_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
        collected_at=now,
    )
    s2 = CivicVoiceSourceRecord(
        id="md-2",
        provider="youtube",
        url="https://youtube.com/watch?v=dasara_highlight",
        author="Namma Mysuru Channel",
        title="Grand Mysore Dasara Illuminated Palace Walkthrough",
        content="Incredible atmosphere at the palace illumination! Such a glorious cultural experience.",
        published_at=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
        collected_at=now,
    )
    s3 = CivicVoiceSourceRecord(
        id="md-3",
        provider="bluesky",
        url="https://bsky.app/profile/citizen/post/333",
        author="@mysore_resident",
        title="Traffic Jam near Bannimantap",
        content="Heavy traffic congestion and lack of parking passes near Bannimantap grounds. Please open more parking shuttle zones.",
        published_at=datetime(2026, 10, 3, 14, 0, tzinfo=timezone.utc),
        collected_at=now,
    )
    source_map = {"md-1": s1, "md-2": s2, "md-3": s3}

    a1 = CivicVoiceAnalysisRecord(
        id="an-1",
        source_record_id="md-1",
        category="neutral_or_informational",
        sentiment="neutral",
        content_intent="news_or_reporting",
        confidence=0.9,
        explanation="Official event schedule",
        theme_id="cultural_events",
        theme_label="Cultural Events & Heritage",
        has_complaint=False,
        has_suggestion=False,
    )
    a2 = CivicVoiceAnalysisRecord(
        id="an-2",
        source_record_id="md-2",
        category="positive_experience",
        sentiment="positive",
        content_intent="first_person_experience",
        confidence=0.95,
        explanation="Palace illumination praise",
        theme_id="cultural_events",
        theme_label="Cultural Events & Heritage",
        has_complaint=False,
        has_suggestion=False,
    )
    a3 = CivicVoiceAnalysisRecord(
        id="an-3",
        source_record_id="md-3",
        category="complaint_or_concern",
        sentiment="negative",
        content_intent="first_person_experience",
        confidence=0.88,
        explanation="Traffic and parking complaints",
        theme_id="traffic_and_transport",
        theme_label="Traffic & Transit Management",
        has_complaint=True,
        extracted_complaint="Heavy traffic congestion and lack of parking passes",
        has_suggestion=True,
        extracted_suggestion="Please open more parking shuttle zones",
    )

    report = synthesizer.generate_summary([a1, a2, a3], source_map, topic="Mysore Dasara 2026")

    # Section A: Topic Introduction
    assert report.topic_title == "Mysore Dasara 2026"
    assert "Mysore Dasara 2026" in report.introduction
    assert report.relevant_dates is not None
    assert "Verified Facts vs. Public Claims" in report.facts_vs_claims

    # Section B: Overall Summary
    assert len(report.overall_summary) > 50
    assert "\n\n" in report.overall_summary  # Synthesized readable paragraphs

    # Section C: Positive Opinions and Highlights
    assert len(report.positive_opinions) >= 1
    pos = report.positive_opinions[0]
    assert pos.supporting_evidence_count == 1
    assert "https://youtube.com/watch?v=dasara_highlight" in pos.source_urls
    assert report.positive_opinions_status is None

    # Section D: Negative Opinions and Criticism
    assert len(report.negative_opinions) >= 1
    neg = report.negative_opinions[0]
    assert neg.supporting_evidence_count == 1
    assert "https://bsky.app/profile/citizen/post/333" in neg.source_urls
    assert report.negative_opinions_status is None

    # Section E: Problems and Concerns
    assert len(report.problems_and_concerns) >= 1
    problem = report.problems_and_concerns[0]
    assert problem.problem_type == "reported_problem"
    assert "congestion" in problem.description.lower() or "parking" in problem.description.lower()

    # Section F: Suggestions and Proposed Improvements
    assert len(report.suggestions_and_improvements) >= 2
    # Verify separation: 1 source author suggestion, 1 synthesized civic recommendation
    source_sug = [s for s in report.suggestions_and_improvements if s.origin == "source_author"]
    synth_sug = [s for s in report.suggestions_and_improvements if s.origin == "synthesized_civicvoice"]
    assert len(source_sug) >= 1
    assert "shuttle" in source_sug[0].suggestion.lower()
    assert len(synth_sug) >= 1
    assert "CivicVoice Synthesized Recommendation" in synth_sug[0].disclaimer

    # Section G: Different Viewpoints and Disagreements
    assert len(report.viewpoint_contrasts) >= 1
    contrast = report.viewpoint_contrasts[0]
    assert len(contrast.areas_of_agreement) > 10
    assert len(contrast.points_of_disagreement) > 10

    # Section H: Trends and Changes Over Time
    assert report.trends_available is True
    assert "2026" in report.trends_overview

    # Section I: Clean Sources List (No raw dump, clean publishers & bounded excerpts)
    assert len(report.clean_sources) == 3
    for cs in report.clean_sources:
        assert len(cs.excerpt) <= 185
        assert cs.publisher != ""
        assert cs.url.startswith("http")
        assert cs.source_type in ("news_reporting", "multimedia_reporting", "public_social_post")

    # Section J: Data Coverage and Limitations
    assert report.coverage.total_source_records == 3
    assert report.coverage.total_analyzed_records == 3
    assert len(report.coverage.limitations) >= 3
    assert "Preliminary sample" in report.sample_size_assessment


def test_universal_report_technology_topic_ai_and_employment():
    """Validates that a non-civic technology query (AI and employment) uses the identical report structure."""
    synthesizer = SummarySynthesizer()
    now = datetime.now(timezone.utc)

    s1 = CivicVoiceSourceRecord(
        id="ai-1",
        provider="tavily",
        url="https://www.thehindu.com/sci-tech/technology/ai-workforce-trends",
        author="The Hindu",
        title="AI Adoption Accelerates in Bengaluru Tech Sector",
        content="Generative AI tools increase programmer productivity but create shifts in entry-level hiring requirements.",
        published_at=datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc),
        collected_at=now,
    )
    s2 = CivicVoiceSourceRecord(
        id="ai-2",
        provider="bluesky",
        url="https://bsky.app/profile/engineer/post/444",
        author="@tech_engineer",
        title="Entry Level Hiring Freeze Discussion",
        content="Junior developers are facing tough hiring slowdowns. Universities should update curriculum to focus on real system architecture.",
        published_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        collected_at=now,
    )
    source_map = {"ai-1": s1, "ai-2": s2}

    a1 = CivicVoiceAnalysisRecord(
        id="an-ai-1",
        source_record_id="ai-1",
        category="positive_experience",
        sentiment="positive",
        content_intent="news_or_reporting",
        confidence=0.92,
        explanation="Productivity gains in tech",
        theme_id="technology_and_innovation",
        theme_label="Technology & Innovation",
        has_complaint=False,
        has_suggestion=False,
    )
    a2 = CivicVoiceAnalysisRecord(
        id="an-ai-2",
        source_record_id="ai-2",
        category="complaint_or_concern",
        sentiment="negative",
        content_intent="first_person_experience",
        confidence=0.89,
        explanation="Junior hiring concerns",
        theme_id="employment_and_economy",
        theme_label="Employment & Economy",
        has_complaint=True,
        extracted_complaint="Junior developers facing hiring slowdowns",
        has_suggestion=True,
        extracted_suggestion="Universities should update curriculum to focus on real system architecture",
    )

    report = synthesizer.generate_summary([a1, a2], source_map, topic="Artificial Intelligence and Employment")

    # The exact same 10-section structure must be present:
    assert report.topic_title == "Artificial Intelligence And Employment"
    assert len(report.positive_opinions) == 1
    assert len(report.negative_opinions) == 1
    assert len(report.problems_and_concerns) == 1
    publishers = [cs.publisher for cs in report.clean_sources]
    assert any("Hindu" in p for p in publishers)
    assert any("Bluesky" in p for p in publishers)


def test_universal_report_honest_empty_states_without_fabrication():
    """Validates that empty results or missing complaints produce honest status without fabricated data."""
    synthesizer = SummarySynthesizer()

    # Case 1: Zero records
    empty_report = synthesizer.generate_summary([], {}, topic="Unknown Topic 9999")
    assert empty_report.topic_title == "Unknown Topic 9999"
    assert len(empty_report.positive_opinions) == 0
    assert "No reliable positive opinions" in empty_report.positive_opinions_status
    assert len(empty_report.negative_opinions) == 0
    assert "No critical or opposing viewpoints" in empty_report.negative_opinions_status
    assert len(empty_report.clean_sources) == 0
    assert empty_report.trends_available is False

    # Case 2: Only positive records (no complaints at all)
    now = datetime.now(timezone.utc)
    s_pos = CivicVoiceSourceRecord(
        id="pos-only",
        provider="bluesky",
        url="https://bsky.app/profile/user/1",
        title="Great New Park in Jayanagar",
        content="Beautiful park with lovely greenery. Excellent initiative by the authorities!",
        published_at=now,
        collected_at=now,
    )
    a_pos = CivicVoiceAnalysisRecord(
        id="an-pos",
        source_record_id="pos-only",
        category="positive_experience",
        sentiment="positive",
        content_intent="first_person_experience",
        confidence=0.96,
        theme_id="parks_and_environment",
        theme_label="Parks & Environment",
        has_complaint=False,
        has_suggestion=False,
    )
    pos_report = synthesizer.generate_summary([a_pos], {"pos-only": s_pos}, topic="Jayanagar New Park")

    assert len(pos_report.positive_opinions) == 1
    assert len(pos_report.negative_opinions) == 0
    assert "No critical, dissatisfied, or opposing viewpoints" in pos_report.negative_opinions_status
    assert len(pos_report.problems_and_concerns) == 0
    assert "No concrete operational hazards" in pos_report.problems_and_concerns_status

