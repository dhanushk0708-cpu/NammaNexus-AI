from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlparse

from app.models.civicvoice import CivicVoiceSourceRecord
from app.schemas.civicvoice import NormalizedSourceRecord


class PreparedEvidenceItem:
    """Standardized, normalized, and classified evidence item prepared for Gemini synthesis."""

    def __init__(
        self,
        source_id: str,
        record_id: str,
        provider: str,
        title: str,
        publisher: str,
        url: str,
        published_at: datetime | None,
        retrieved_at: datetime,
        excerpt: str,
        source_type: str,
        is_opinion_bearing: bool,
        relevance_score: float,
        language: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.source_id = source_id
        self.record_id = record_id
        self.provider = provider
        self.title = title
        self.publisher = publisher
        self.url = url
        self.published_at = published_at
        self.retrieved_at = retrieved_at
        self.excerpt = excerpt
        self.source_type = source_type
        self.is_opinion_bearing = is_opinion_bearing
        self.relevance_score = relevance_score
        self.language = language
        self.metadata = metadata or {}

    def to_gemini_evidence_block(self) -> str:
        """Serializes the evidence item safely as untrusted data for LLM ingestion."""
        pub_date_str = self.published_at.strftime("%Y-%m-%d") if self.published_at else "Unknown date"
        opinion_tag = "OPINION_BEARING" if self.is_opinion_bearing else "INFORMATIONAL_OR_FACTUAL"
        clean_text = self.excerpt.replace("<", "&lt;").replace(">", "&gt;")
        return (
            f'<evidence_item id="{self.source_id}">\n'
            f'  <title>{self.title}</title>\n'
            f'  <publisher>{self.publisher}</publisher>\n'
            f'  <source_type>{self.source_type}</source_type>\n'
            f'  <nature>{opinion_tag}</nature>\n'
            f'  <published_date>{pub_date_str}</published_date>\n'
            f'  <url>{self.url}</url>\n'
            f'  <content_excerpt>{clean_text}</content_excerpt>\n'
            f'</evidence_item>'
        )


class EvidencePreparer:
    """Normalizes, deduplicates, assesses semantic relevance, and classifies sources for research."""

    STOP_WORDS = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
        "is", "are", "was", "were", "with", "by", "from", "as", "about",
        "what", "how", "why", "who", "which", "when", "where", "it", "this", "that",
    }

    OFFICIAL_DOMAINS = [
        ".gov.in", ".nic.in", "karnataka.gov", "bbmp.gov.in", "mysuru.nic.in",
        "mysore.nic.in", "bmrc.co.in", "bengalurumerorail", "ksp.gov.in",
        "bescom.org", "bwssb.karnataka.gov.in", "pib.gov.in",
    ]

    NEWS_DOMAINS = [
        "thehindu.com", "deccanherald.com", "timesofindia.indiatimes.com",
        "indianexpress.com", "hindustantimes.com", "ndtv.com", "bbc.com",
        "reuters.com", "theprint.in", "scroll.in", "thenewsminute.com",
        "livemint.com", "moneycontrol.com", "economictimes.indiatimes.com",
    ]

    INJECTION_PATTERNS = [
        r"(?i)ignore\s+(all\s+|previous\s+|prior\s+)?instructions",
        r"(?i)system\s*prompt\s*:",
        r"(?i)you\s+are\s+now\s+(an?\s+)?ai",
        r"(?i)forget\s+everything",
        r"(?i)override\s+previous",
    ]

    def sanitize_untrusted_text(self, text: str | None) -> str:
        """Sanitizes source text to neutralize prompt injection directives and control chars."""
        if not text:
            return ""
        cleaned = text
        for pat in self.INJECTION_PATTERNS:
            cleaned = re.sub(pat, "[FILTERED_DIRECTIVE]", cleaned)
        # Strip excessive control characters
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def derive_publisher(self, provider: str, author: str | None, url: str) -> str:
        """Extracts a human-readable publisher name."""
        if provider == "bluesky":
            if author:
                clean_a = author.strip()
                return f"Bluesky ({clean_a})" if not clean_a.lower().startswith("bluesky") else clean_a
            return "Bluesky"

        if author and not author.startswith("http") and not author.startswith("www.") and len(author) <= 40:
            return author.strip()

        if url:
            try:
                host = urlparse(url).netloc.replace("www.", "")
                parts = host.split(".")
                if len(parts) >= 2:
                    return parts[0].replace("-", " ").title()
            except Exception:
                pass

        return provider.capitalize()

    def classify_source_type(self, url: str, provider: str, content: str | None) -> str:
        """Classifies source record into standard civic information categories."""
        url_lower = (url or "").lower()

        if any(d in url_lower for d in self.OFFICIAL_DOMAINS):
            return "official_information"

        if provider == "youtube":
            return "multimedia"

        if provider == "bluesky":
            return "public_opinion"

        if any(d in url_lower for d in self.NEWS_DOMAINS):
            return "news_reporting"

        if "wikipedia.org" in url_lower or "wikivoyage.org" in url_lower or "britannica.com" in url_lower:
            return "informational_content"

        return "news_reporting" if provider == "tavily" else "informational_content"

    def is_opinion_bearing_content(self, source_type: str, text: str | None) -> bool:
        """Determines if a source contains genuine subjective opinions, citizen sentiment, or reviews."""
        if source_type in ("public_opinion", "community_opinion"):
            return True

        if source_type == "official_information":
            return False

        if not text:
            return False

        lower_text = text.lower()
        opinion_markers = [
            "i feel", "i think", "in my opinion", "we faced", "frustrated", "terrible",
            "horrible", "amazing", "wonderful", "delighted", "complaint", "waste of time",
            "crowded", "poorly managed", "disappointing", "great job", "kudos",
            "traffic jam", "not worth it", "exorbitant", "overpriced", "corrupt",
            "demanded", "suggested", "protested", "criticized", "praised", "hailed",
        ]
        return any(marker in lower_text for marker in opinion_markers)

    CITY_SYNONYMS = {
        "mysore": "mysuru",
        "mysuru": "mysore",
        "bangalore": "bengaluru",
        "bengaluru": "bangalore",
    }

    def assess_relevance(self, query: str, title: str | None, content: str | None, topic: str | None, url: str | None) -> float:
        """Calculates semantic keyword and entity overlap score between query and source record."""
        clean_q = (query or "").lower().strip()
        tokens = [t for t in re.findall(r"\b[a-zA-Z0-9_\u0C80-\u0CFF]+\b", clean_q) if t not in self.STOP_WORDS]
        if not tokens:
            return 1.0

        title_lower = (title or "").lower()
        content_lower = (content or "").lower()
        url_lower = (url or "").lower()

        # Check full query phrase exact match in title or content (exclude topic as topic is our own query tag)
        if len(tokens) >= 2 and clean_q in f"{title_lower} {content_lower}":
            return 1.0

        score = 0.0
        primary_entities = [t for t in tokens if not t.isdigit() and len(t) > 2]

        matched_tokens = 0
        for t in tokens:
            syn = self.CITY_SYNONYMS.get(t)
            if t in title_lower or (syn and syn in title_lower):
                score += 0.4
                matched_tokens += 1
            elif t in url_lower or (syn and syn in url_lower):
                score += 0.2
                matched_tokens += 1
            elif t in content_lower or (syn and syn in content_lower):
                score += 0.15
                matched_tokens += 1

        # Reject records where only incidental numbers or generic words matched, missing core topic entities
        if primary_entities:
            entity_matches = sum(
                1 for e in primary_entities
                if e in title_lower or e in content_lower or e in url_lower
                or (self.CITY_SYNONYMS.get(e) and (self.CITY_SYNONYMS[e] in title_lower or self.CITY_SYNONYMS[e] in content_lower or self.CITY_SYNONYMS[e] in url_lower))
            )
            coverage = entity_matches / len(primary_entities)
            if coverage < 0.5:
                # Less than half of the distinct primary topic words were found in the source
                return 0.05 * coverage

        normalized_score = min(1.0, score / max(1, len(tokens) * 0.3))
        return normalized_score

    def prepare_evidence(
        self,
        query: str,
        records: list[CivicVoiceSourceRecord | NormalizedSourceRecord],
        min_relevance: float = 0.2,
    ) -> tuple[list[PreparedEvidenceItem], list[PreparedEvidenceItem]]:
        """Deduplicates, scores, classifies, and prepares evidence items.

        Returns (relevant_evidence_items, filtered_out_items).
        """
        now = datetime.now(timezone.utc)
        seen_urls: set[str] = set()
        seen_keys: set[str] = set()

        relevant_items: list[PreparedEvidenceItem] = []
        filtered_items: list[PreparedEvidenceItem] = []
        item_counter = 1

        for r in records:
            url = (r.url or "").strip()
            if not url or url in seen_urls:
                continue

            dedup = getattr(r, "dedup_key", None)
            if dedup and dedup in seen_keys:
                continue

            seen_urls.add(url)
            if dedup:
                seen_keys.add(dedup)

            title = (r.title or "").strip()
            raw_content = getattr(r, "content", "") or ""
            content = self.sanitize_untrusted_text(raw_content)
            topic = getattr(r, "topic", None) or ""
            provider = (getattr(r, "provider", None) or "web").strip().lower()
            rec_id = getattr(r, "id", None) or dedup or f"rec_{item_counter}"
            author = getattr(r, "author", None)
            published_at = getattr(r, "published_at", None)
            retrieved_at = getattr(r, "collected_at", None) or now
            language = getattr(r, "language", None)

            relevance = self.assess_relevance(query, title, content, topic, url)
            source_type = self.classify_source_type(url, provider, content)
            is_opinion = self.is_opinion_bearing_content(source_type, content)
            publisher = self.derive_publisher(provider, author, url)

            # Produce clean bounded excerpt
            excerpt = content[:600] if len(content) > 600 else content
            if not excerpt:
                excerpt = f"Source publication titled '{title}' covering {query}."

            source_id = f"SRC-{item_counter}"
            item = PreparedEvidenceItem(
                source_id=source_id,
                record_id=rec_id,
                provider=provider,
                title=title or f"Document regarding {query}",
                publisher=publisher,
                url=url,
                published_at=published_at,
                retrieved_at=retrieved_at,
                excerpt=excerpt,
                source_type=source_type,
                is_opinion_bearing=is_opinion,
                relevance_score=relevance,
                language=language,
                metadata=getattr(r, "metadata_json", None) or {},
            )

            if relevance >= min_relevance:
                relevant_items.append(item)
                item_counter += 1
            else:
                filtered_items.append(item)

        # Sort relevant items by relevance score descending
        relevant_items.sort(key=lambda x: x.relevance_score, reverse=True)
        return relevant_items, filtered_items
