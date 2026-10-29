import logging
import re
from typing import Any
from app.services.nammaserve.ai.cache import (
    IntentCache,
    get_default_intent_cache,
    normalize_intent_cache_key,
)
from app.services.nammaserve.ai.providers.factory import get_primary_and_secondary
from app.services.nammaserve.ai.providers.manager import ProviderManager
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.nammaserve import VerificationStatus
from app.schemas.nammaserve import (
    AssistantChatRequest,
    AssistantChatResponse,
    DiscoveryQuery,
    NormalizedProviderResult,
    ServiceIntent,
    ToolCallRecord,
)
from app.services.nammaserve.ai.prompts import (
    GROUNDED_RESPONSE_SYSTEM_PROMPT,
    INTENT_EXTRACTION_SYSTEM_PROMPT,
)
from app.services.nammaserve.discovery.resolver import CatalogueResolver
from app.services.nammaserve.discovery.service import UnifiedDiscoveryService

logger = logging.getLogger(__name__)

BENGALURU_LOCALITIES = [
    "kengeri",
    "hsr layout",
    "hsr",
    "indiranagar",
    "koramangala",
    "whitefield",
    "jayanagar",
    "malleswaram",
    "hebbal",
    "yelahanka",
    "marathahalli",
    "electronic city",
    "banashankari",
    "btm layout",
    "btm",
    "rajajinagar",
    "kammanahalli",
    "bellandur",
    "sarjapur",
    "domlur",
    "richmond town",
    "basavanagudi",
]


class ServiceAssistant:
    """NammaServe AI Assistant: orchestrates natural language intent understanding,

    deterministic tool execution via UnifiedDiscoveryService, and grounded response synthesis.
    """

    def __init__(
        self,
        db: Session,
        discovery_service: UnifiedDiscoveryService | None = None,
        llm: Any = None,
        intent_cache: IntentCache | None = None,
    ):
        self.db = db
        self.discovery_service = discovery_service or UnifiedDiscoveryService(db=db)
        self.llm = llm
        self.intent_cache = intent_cache if intent_cache is not None else get_default_intent_cache()
        if self.llm is None:
            primary, secondary = get_primary_and_secondary()
            self.provider_manager = ProviderManager(primary, secondary)
        else:
            self.provider_manager = None

    def _get_llm(self) -> Any:
        """Return the injected LLM if provided; otherwise let ProviderManager handle provider selection.

        When a custom `llm` is supplied (e.g., in tests), it is returned directly.
        In normal operation the method returns ``None`` and callers should use
        ``self.provider_manager`` to obtain a chat model with fallback handling.
        """
        if self.llm is not None:
            return self.llm
        return None

    @staticmethod
    def _preserve_contact_fact(reply: str, results: list[NormalizedProviderResult]) -> str:
        """Ensure a sourced contact detail is not omitted by an otherwise grounded answer."""
        if not results:
            return reply
        top = results[0]
        if top.phone and top.phone not in {"Not Available", "Contact via Platform"} and top.phone not in reply:
            return f"{reply.rstrip()} Contact: {top.phone}."
        return reply

    async def parse_intent(
        self,
        message: str,
        request_id: str | None = None,
    ) -> tuple[ServiceIntent, bool]:
        """Extract structured service intent from user message using cache, LLM, or deterministic fallback."""
        cache_key = normalize_intent_cache_key(message)

        # 1. Check Intent Cache (HIT: returns cached ServiceIntent without invoking LLM/telemetry)
        if self.intent_cache is not None:
            try:
                cached_intent = self.intent_cache.get(cache_key)
                if cached_intent is not None:
                    logger.debug("Intent cache HIT for key '%s'", cache_key)
                    return (cached_intent, False)
            except Exception as c_get_exc:
                logger.warning("Intent cache lookup failed: %s; proceeding to LLM extraction.", c_get_exc)

        # 2. Cache MISS -> LLM Extraction
        # If a custom LLM is injected, use it directly (no fallback).
        if self.llm is not None:
            llm = self._get_llm()
            try:
                structured_llm = llm.with_structured_output(ServiceIntent)
                messages = [
                    SystemMessage(content=INTENT_EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(content=message),
                ]
                result = await structured_llm.ainvoke(messages)
                parsed_intent: ServiceIntent | None = None
                if isinstance(result, ServiceIntent):
                    parsed_intent = result
                elif isinstance(result, dict):
                    parsed_intent = ServiceIntent(**result)

                if parsed_intent is not None:
                    if self.intent_cache is not None:
                        try:
                            self.intent_cache.set(cache_key, parsed_intent)
                        except Exception as c_set_exc:
                            logger.warning("Failed to store intent in cache: %s", c_set_exc)
                    return (parsed_intent, False)
            except Exception as exc:
                logger.warning("LLM structured intent parsing failed (%s); using fallback parser.", exc)

        # Use ProviderManager for primary/secondary fallback when no custom llm.
        async def operation(model):
            structured_llm = model.with_structured_output(ServiceIntent)
            messages = [
                SystemMessage(content=INTENT_EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=message),
            ]
            return await structured_llm.ainvoke(messages)

        if self.provider_manager is not None:
            try:
                result = await self.provider_manager.run_with_fallback(
                    operation=operation,
                    request_id=request_id,
                    operation_name="intent_extraction",
                )
                parsed_intent: ServiceIntent | None = None
                if isinstance(result, ServiceIntent):
                    parsed_intent = result
                elif isinstance(result, dict):
                    parsed_intent = ServiceIntent(**result)

                if parsed_intent is not None:
                    if self.intent_cache is not None:
                        try:
                            self.intent_cache.set(cache_key, parsed_intent)
                        except Exception as c_set_exc:
                            logger.warning("Failed to store intent in cache: %s", c_set_exc)
                    return (parsed_intent, False)
            except Exception as exc:
                logger.warning("LLM structured intent parsing failed (%s); using fallback parser.", exc)

        # Fallback deterministic parser
        fallback_intent = self._fallback_parse_intent(message)
        return (fallback_intent, True)

    def _fallback_parse_intent(self, message: str) -> ServiceIntent:
        """Deterministic keyword and regex-based intent parser."""
        text = message.lower()

        # 1. Service classification
        service = None
        if any(w in text for w in ["bathroom", "toilet", "mane clean", "house clean", "home clean"]):
            service = "bathroom-deep-cleaning" if any(
                w in text for w in ["bathroom", "toilet"]
            ) else "full-home-deep-cleaning-1bhk"
        elif any(w in text for w in ["tank clean", "tank cleaning", "neerina tank", "overhead tank"]):
            service = "overhead-tank-cleaning"
        elif any(w in text for w in ["ac mechanic", "ac service", "ac repair", "ac servicing", "ac service madisbeku"]):
            service = "ac-repair"
        elif any(w in text for w in ["plumb", "plumbing", "pipe", "bathroom fitting"]):
            service = "plumbing"
        elif any(w in text for w in ["water", "tanker", "cauvery", "kaveri", "potable", "neeru"]):
            service = "water-tanker"
        elif any(w in text for w in ["lock", "key", "lockout", "locksmith", "keymaker"]):
            service = "locksmith-emergency"
        elif any(w in text for w in ["solar", "water heater", "solar heater"]):
            service = "solar-heater-repair"
        elif any(w in text for w in ["e-waste", "ewaste", "electronic", "laptop recycle", "computer scrap"]):
            service = "e-waste-pickup"
        elif any(w in text for w in ["debris", "construction", "rubble", "bulk waste", "waste pickup"]):
            service = "debris-bulk-waste"

        # 2. Location extraction
        location = None
        for loc in BENGALURU_LOCALITIES:
            if loc in text:
                location = loc.title()
                break
        if location is None:
            transliterated_localities = {
                "rajajinagar": "Rajajinagar",
                "rajajinagara": "Rajajinagar",
                "rajajinagara alli": "Rajajinagar",
                "indiranagara": "Indiranagar",
                "kengeriyalli": "Kengeri",
                "malleshwaram": "Malleswaram",
            }
            for marker, locality in transliterated_localities.items():
                if marker in text:
                    location = locality
                    break

        # 3. Radius extraction (e.g., "within 5 km", "in 10km")
        radius_km = None
        radius_match = re.search(r"(?:within|in|around)\s*(\d+(?:\.\d+)?)\s*km", text)
        if radius_match:
            try:
                radius_km = float(radius_match.group(1))
            except ValueError:
                pass

        # 4. Capacity extraction (e.g. "6000 litre", "6000L", "4000 litres")
        capacity_litres = None
        cap_match = re.search(r"(\d+)\s*(?:l|litre|litres|liter|liters)\b", text)
        if cap_match:
            try:
                capacity_litres = float(cap_match.group(1))
            except ValueError:
                pass

        # 5. Urgency extraction
        urgent = any(w in text for w in ["urgent", "urgently", "emergency", "immediately", "24x7", "night", "locked out", "asap"])

        return ServiceIntent(
            service=service,
            location=location,
            radius_km=radius_km,
            capacity_litres=capacity_litres,
            urgent=urgent,
        )

    async def generate_grounded_reply(
        self,
        message: str,
        intent: ServiceIntent,
        results: list[NormalizedProviderResult],
        request_id: str | None = None,
    ) -> str:
        """Synthesize a grounded answer using retrieved factual providers only."""
        # If a custom LLM is injected, use it directly.
        if self.llm is not None:
            llm = self._get_llm()
            try:
                context_summary = []
                for idx, r in enumerate(results[:5], start=1):
                    pricing = r.formatted_price or "Price not publicly listed"
                    dist = f"{r.distance_km:.1f} km away" if r.distance_km is not None else "Distance N/A"
                    badge = r.verification_status.value if isinstance(r.verification_status, VerificationStatus) else str(r.verification_status)
                    context_summary.append(
                        f"{idx}. {r.name} - {r.area or r.city} [{dist}] - Price: {pricing}; pricing type: {r.price_type or 'not stated'}; source: {r.source_url or 'not supplied'}; verified: {r.last_verified_at or 'not supplied'}; status: {badge}"
                    )

                context_text = "\n".join(context_summary) if context_summary else "NO_PROVIDERS_FOUND"

                prompt = (
                    f"Citizen Query: {message}\n"
                    f"Extracted Intent: Service={intent.service}, Location={intent.location}, Urgent={intent.urgent}\n\n"
                    f"Factual Retrieved Providers and pricing:\n{context_text}\n\n"
                    f"Please provide a helpful, grounded response summarizing these options."
                )

                messages = [
                    SystemMessage(content=GROUNDED_RESPONSE_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
                reply_msg = await llm.ainvoke(messages)
                return self._preserve_contact_fact(reply_msg.content.strip(), results)
            except Exception as exc:
                logger.warning("LLM grounded reply synthesis failed (%s); using template reply.", exc)

        # Use ProviderManager fallback when no custom llm.
        async def operation(model):
            context_summary = []
            for idx, r in enumerate(results[:5], start=1):
                pricing = r.formatted_price or "Price not publicly listed"
                dist = f"{r.distance_km:.1f} km away" if r.distance_km is not None else "Distance N/A"
                badge = r.verification_status.value if isinstance(r.verification_status, VerificationStatus) else str(r.verification_status)
                context_summary.append(
                    f"{idx}. {r.name} - {r.area or r.city} [{dist}] - Price: {pricing}; pricing type: {r.price_type or 'not stated'}; source: {r.source_url or 'not supplied'}; verified: {r.last_verified_at or 'not supplied'}; status: {badge}"
                )
            context_text = "\n".join(context_summary) if context_summary else "NO_PROVIDERS_FOUND"
            prompt = (
                f"Citizen Query: {message}\n"
                f"Extracted Intent: Service={intent.service}, Location={intent.location}, Urgent={intent.urgent}\n\n"
                f"Factual Retrieved Providers:\n{context_text}\n\n"
                f"Please provide a helpful, grounded response summarizing these options."
            )
            messages = [
                SystemMessage(content=GROUNDED_RESPONSE_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            reply_msg = await model.ainvoke(messages)
            return reply_msg.content.strip()

        try:
            reply = await self.provider_manager.run_with_fallback(
                operation=operation,
                request_id=request_id,
                operation_name="grounded_response",
            )
            return self._preserve_contact_fact(reply, results)
        except Exception as exc:
            logger.warning("LLM grounded reply synthesis failed (%s); using template reply.", exc)

        # Deterministic template reply
        if not results:
            loc_str = f" in or near {intent.location}" if intent.location else ""
            svc_str = intent.service.replace("-", " ") if intent.service else "civic service"
            return (
                f"Namaskara! We could not find any active {svc_str} providers{loc_str} matching your exact criteria. "
                f"You can try expanding your search radius or contact the local BBMP/civic control room."
            )

        top = results[0]
        dist_info = f" ({top.distance_km:.1f} km away)" if top.distance_km is not None else ""
        price_info = f" with sourced pricing {top.formatted_price}" if top.formatted_price and top.is_price_available else ""
        return (
            f"Namaskara! Found {len(results)} option(s) for your request. "
            f"Top match: {top.name}{dist_info}{price_info}. "
            f"Source: {top.source_url or 'not supplied'}."
        )

    async def process_chat(
        self,
        request: AssistantChatRequest,
        request_id: str | None = None,
    ) -> AssistantChatResponse:
        """End-to-end processing: parse intent -> call deterministic tools -> synthesize reply."""
        from uuid import uuid4
        req_id = request_id or str(uuid4())

        intent, fallback_used = await self.parse_intent(request.message, request_id=req_id)
        if not intent.service:
            return AssistantChatResponse(
                message=request.message,
                intent=intent,
                reply="Which service do you need help with, and in which Bengaluru locality?",
                fallback_used=fallback_used,
            )
        if intent.service:
            canonical_aliases = {
                "debris-pickup": "debris-bulk-waste",
                "bathroom-cleaning": "bathroom-deep-cleaning",
                "home-cleaning": "full-home-deep-cleaning-1bhk",
                "ac-mechanic": "ac-repair",
            }
            intent.service = canonical_aliases.get(intent.service.lower(), intent.service)
            resolved = CatalogueResolver.resolve(intent.service, db=self.db)
            if isinstance(resolved.service_slug, str) and resolved.service_slug:
                intent.service = resolved.service_slug
            elif (
                isinstance(resolved.category_slug, str)
                and resolved.category_slug
                and resolved.match_level.value != "UNCONFIRMED"
            ):
                intent.service = resolved.category_slug

        # Build deterministic tool call
        location = intent.location or request.user_area
        radius_km = intent.radius_km or settings.default_search_radius_km

        tool_args = {
            "service": intent.service,
            "location": location,
            "lat": request.lat,
            "lng": request.lng,
            "radius_km": radius_km,
            "urgent": intent.urgent,
        }

        tool_calls = [
            ToolCallRecord(
                tool_name="search_local_services",
                tool_arguments=tool_args,
            )
        ]

        # Execute deterministic search (urgency is ranked and prioritized by RankingEngine)
        query = DiscoveryQuery(
            service=intent.service,
            area=location,
            lat=request.lat,
            lng=request.lng,
            radius_km=radius_km,
            emergency_only=False,
        )

        discovery_response = await self.discovery_service.discover(query)
        results = discovery_response.results

        # Generate grounded reply
        reply = await self.generate_grounded_reply(
            message=request.message,
            intent=intent,
            results=results,
            request_id=req_id,
        )

        return AssistantChatResponse(
            message=request.message,
            intent=intent,
            tool_calls=tool_calls,
            discovery_results=results,
            price_comparison=discovery_response.price_comparison,
            reply=reply,
            fallback_used=fallback_used,
        )
