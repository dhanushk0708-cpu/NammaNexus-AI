import re
from typing import Any

from app.models.civicvoice import CivicVoiceSourceRecord
from app.schemas.civicvoice import (
    ContentIntent,
    OpinionCategory,
    SentimentLabel,
)
from app.services.civicvoice.intelligence.base import (
    AnalyzedOpinionResult,
    BaseOpinionAnalyzer,
    detect_text_language,
)

# ---------------------------------------------------------------------------
# Multilingual Lexical & Pattern Constants (English + Kannada)
# ---------------------------------------------------------------------------

KANNADA_POSITIVE_SIGNALS = {
    "ಧನ್ಯವಾದ", "ಉತ್ತಮ", "ಚೆನ್ನಾಗಿದೆ", "ಅದ್ಭುತ", "ಮೆಚ್ಚುಗೆ", "ಖುಷಿ", "ಉಪಯುಕ್ತ", "ಸ್ವಾಗತಾರ್ಹ", "ಹಿತಕರ",
}

KANNADA_COMPLAINT_SIGNALS = {
    "ಗುಂಡಿ", "ಕಸ", "ಸಮಸ್ಯೆ", "ಕೆಟ್ಟ", "ತೊಂದರೆ", "ವಿಳಂಬ", "ಟ್ರಾಫಿಕ್", "ನೀರಿಲ್ಲ",
    "ಹಾಳಾಗಿದೆ", "ಅವ್ಯವಸ್ಥೆ", "ವಾಸನೆ", "ದುರ್ವಾಸನೆ", "ಅಪಾಯಕಾರಿ", "ಬೇಗ ಸರಿಮಾಡಿ", "ಅಧಿಕಾರಿಗಳ ನಿರ್ಲಕ್ಷ್ಯ",
}

KANNADA_SUGGESTION_SIGNALS = {
    "ದಯವಿಟ್ಟು", "ಮಾಡಬೇಕು", "ಸಲಹೆ", "ಕ್ರಮ ಕೈಗೊಳ್ಳಿ", "ಹೆಚ್ಚಿಸಿ", "ಬದಲಾಯಿಸಿ", "ಮಾಡಬೇಕಾಗಿದೆ",
    "ಅಗತ್ಯವಿದೆ", "ನಿರ್ಮಿಸಿ", "ಆಗ್ರಹ",
}

KANNADA_QUESTION_SIGNALS = {
    "ಯಾವಾಗ", "ಹೇಗೆ", "ಎಲ್ಲಿ", "ಏಕೆ", "ಮಾಹಿತಿ ನೀಡಿ", "ತಿಳಿಸಿ",
}

KANNADA_FIRST_PERSON_SIGNALS = {
    "ನಾನು", "ನನ್ನ", "ನಮ್ಮ", "ನನಗೆ", "ನಾವೆಲ್ಲ", "ಕಂಡೆ",
}

KANNADA_NEWS_SIGNALS = {
    "ವರದಿ", "ಸುದ್ದಿ", "ತಿಳಿಸಿದೆ", "ಘೋಷಿಸಿದೆ", "ಮಾಧ್ಯಮ", "ಪ್ರಕಟಣೆ",
}

ENGLISH_POSITIVE_SIGNALS = {
    "thank", "thanks", "great", "excellent", "appreciate", "kudos", "good work",
    "well done", "improved", "clean", "smooth", "happy", "commendable",
}

ENGLISH_COMPLAINT_SIGNALS = {
    "pothole", "potholes", "garbage", "trash", "broken", "worst", "traffic jam",
    "waterlogging", "stench", "leakage", "overflow", "terrible", "delay", "danger",
    "hazardous", "filthy", "neglect", "pathetic", "dark street", "power cut",
}

ENGLISH_SUGGESTION_SIGNALS = {
    "please", "suggest", "suggestion", "recommend", "recommendation", "should add",
    "should provide", "need to improve", "request to", "kindly", "construct",
    "deploy", "install", "must fix", "ought to",
}

ENGLISH_QUESTION_SIGNALS = {
    "when will", "how can", "is there", "where can", "why is", "any update",
}

ENGLISH_FIRST_PERSON_SIGNALS = {
    "i saw", "i experienced", "my street", "our road", "near my house", "i was stuck",
    "we faced", "daily commute", "i commute", "my area",
}

ENGLISH_NEWS_SIGNALS = {
    "reported", "according to", "police say", "officials stated", "bbmp announced",
    "bengaluru news", "press release", "news report", "sources say", "spokesperson",
}

ENGLISH_PROMO_SIGNALS = {
    "discount", "buy now", "sale", "order today", "special offer", "register now", "call us for",
}


class RuleBasedMultilingualAnalyzer(BaseOpinionAnalyzer):
    """Deterministic multilingual opinion analyzer supporting English and Kannada.

    Provides explainable, evidence-grounded classification without external network dependency.
    """

    METHOD_NAME = "rule_based_multilingual"
    VERSION = "v1.0"

    def _extract_clauses(self, text: str) -> list[str]:
        """Splits text into sentences or clause units."""
        raw_parts = re.split(r"[\n.!?।]+", text)
        return [p.strip() for p in raw_parts if len(p.strip()) > 3]

    def analyze_record(self, record: CivicVoiceSourceRecord) -> AnalyzedOpinionResult:
        """Examines the title, content, and metadata to produce a structured opinion result."""
        text = ((record.title or "") + " " + (record.content or "")).strip()

        if not text or len(text) < 5:
            return AnalyzedOpinionResult(
                category=OpinionCategory.UNCLEAR_OR_INSUFFICIENT,
                sentiment=SentimentLabel.UNCERTAIN,
                content_intent=ContentIntent.UNCLEAR_INTENT,
                confidence="uncertain",
                explanation="Source record contains insufficient or empty descriptive text.",
                detected_language="unknown",
                has_complaint=False,
                has_suggestion=False,
                analysis_method=self.METHOD_NAME,
                analysis_version=self.VERSION,
            )

        detected_lang = detect_text_language(text)
        lower_text = text.lower()
        clauses = self._extract_clauses(text)

        # 1. Determine Content Intent
        is_promo = any(term in lower_text for term in ENGLISH_PROMO_SIGNALS)
        is_news = any(term in lower_text for term in ENGLISH_NEWS_SIGNALS | KANNADA_NEWS_SIGNALS)
        has_en_first_person = bool(re.search(r"\b(i|my|we|our|me|mine)\b", lower_text))
        has_kn_first_person = any(term in lower_text for term in KANNADA_FIRST_PERSON_SIGNALS)
        is_first_person = has_en_first_person or has_kn_first_person

        if is_promo:
            intent = ContentIntent.PROMOTIONAL_MATERIAL
        elif is_news:
            intent = ContentIntent.NEWS_OR_REPORTING
        elif is_first_person:
            intent = ContentIntent.FIRST_PERSON_EXPERIENCE
        else:
            intent = ContentIntent.GENERAL_OPINION

        # 2. Extract Signals
        has_positive = any(term in lower_text for term in ENGLISH_POSITIVE_SIGNALS | KANNADA_POSITIVE_SIGNALS)
        has_negative = any(term in lower_text for term in ENGLISH_COMPLAINT_SIGNALS | KANNADA_COMPLAINT_SIGNALS)
        has_suggestion = any(term in lower_text for term in ENGLISH_SUGGESTION_SIGNALS | KANNADA_SUGGESTION_SIGNALS)
        has_question = ("?" in text) or any(term in lower_text for term in ENGLISH_QUESTION_SIGNALS | KANNADA_QUESTION_SIGNALS)

        # Extract specific complaint and suggestion sentences
        extracted_complaint: str | None = None
        extracted_suggestion: str | None = None

        for clause in clauses:
            cl_lower = clause.lower()
            if not extracted_complaint and any(t in cl_lower for t in ENGLISH_COMPLAINT_SIGNALS | KANNADA_COMPLAINT_SIGNALS):
                extracted_complaint = clause
            if not extracted_suggestion and any(t in cl_lower for t in ENGLISH_SUGGESTION_SIGNALS | KANNADA_SUGGESTION_SIGNALS):
                extracted_suggestion = clause

        # If flagged but no single clause isolated, use whole text truncated
        if has_negative and not extracted_complaint:
            extracted_complaint = text[:250]
        if has_suggestion and not extracted_suggestion:
            extracted_suggestion = text[:250]

        # 3. Categorization & Sentiment
        category = OpinionCategory.NEUTRAL_OR_INFORMATIONAL
        sentiment = SentimentLabel.NEUTRAL
        confidence = "medium"
        explanation = "Neutral or informational civic statement."

        if is_promo:
            category = OpinionCategory.NEUTRAL_OR_INFORMATIONAL
            sentiment = SentimentLabel.NEUTRAL
            explanation = "Promotional or commercial content; excluded from first-person civic sentiment."
        elif has_positive and has_negative:
            category = OpinionCategory.MIXED_OPINION
            sentiment = SentimentLabel.MIXED
            explanation = "Content expresses contrasting positive and negative observations."
        elif has_negative:
            category = OpinionCategory.COMPLAINT_OR_CONCERN
            sentiment = SentimentLabel.NEGATIVE
            confidence = "high"
            explanation = f"Complaint identified regarding civic issue: '{extracted_complaint[:100]}...'"
        elif has_suggestion:
            category = OpinionCategory.SUGGESTION_OR_RECOMMENDATION
            sentiment = SentimentLabel.NEUTRAL
            confidence = "medium"
            explanation = f"Community recommendation extracted: '{extracted_suggestion[:100]}...'"
        elif has_positive:
            category = OpinionCategory.POSITIVE_EXPERIENCE
            sentiment = SentimentLabel.POSITIVE
            confidence = "high"
            explanation = "Appreciation or positive civic experience expressed."
        elif has_question:
            category = OpinionCategory.QUESTION_OR_REQUEST
            sentiment = SentimentLabel.NEUTRAL
            explanation = "Citizen inquiry or request for civic information."
        else:
            category = OpinionCategory.NEUTRAL_OR_INFORMATIONAL
            sentiment = SentimentLabel.NEUTRAL
            explanation = "Informational observation without explicit sentiment markers."

        return AnalyzedOpinionResult(
            category=category,
            sentiment=sentiment,
            content_intent=intent,
            confidence=confidence,
            explanation=explanation,
            detected_language=detected_lang,
            has_complaint=bool(extracted_complaint),
            extracted_complaint=extracted_complaint,
            has_suggestion=bool(extracted_suggestion),
            extracted_suggestion=extracted_suggestion,
            theme_id=None,  # Themes are assigned by clustering/theming engine
            theme_label=None,
            analysis_method=self.METHOD_NAME,
            analysis_version=self.VERSION,
        )
