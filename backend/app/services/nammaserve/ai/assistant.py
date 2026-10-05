import logging
import re
from typing import Any
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
    ):
        self.db = db
        self.discovery_service = discovery_service or UnifiedDiscoveryService(db=db)
        self.llm = llm

    def _get_llm(self) -> Any:
        if self.llm is not None:
            return self.llm
        if settings.gemini_api_key:
            return ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.1,
            )
        return None

    async def parse_intent(self, message: str) -> tuple[ServiceIntent, bool]:
        """Extract structured service intent from user message using LLM or deterministic fallback."""
        llm = self._get_llm()
        if llm:
            try:
                structured_llm = llm.with_structured_output(ServiceIntent)
                messages = [
                    SystemMessage(content=INTENT_EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(content=message),
                ]
                result = await structured_llm.ainvoke(messages)
                if isinstance(result, ServiceIntent):
                    return (result, False)
                if isinstance(result, dict):
                    return (ServiceIntent(**result), False)
            except Exception as exc:
                logger.warning("LLM structured intent parsing failed (%s); using fallback parser.", exc)

        # Fallback deterministic rule-based parser
        fallback_intent = self._fallback_parse_intent(message)
        return (fallback_intent, True)

    def _fallback_parse_intent(self, message: str) -> ServiceIntent:
        """Deterministic keyword and regex-based intent parser."""
        text = message.lower()

        # 1. Service classification
        service = None
        if any(w in text for w in ["water", "tanker", "cauvery", "kaveri", "potable"]):
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
    ) -> str:
        """Synthesize a grounded answer using retrieved factual providers only."""
        llm = self._get_llm()
        if llm:
            try:
                context_summary = []
                for idx, r in enumerate(results[:5], start=1):
                    pricing = f"₹{int(r.price_min)} - ₹{int(r.price_max)} {r.price_unit or ''}" if r.price_min else "Price on request"
                    dist = f"{r.distance_km:.1f} km away" if r.distance_km is not None else "Distance N/A"
                    badge = "VERIFIED" if r.verification_status == VerificationStatus.VERIFIED else "UNVERIFIED"
                    context_summary.append(
                        f"{idx}. {r.name} ({r.phone}) - {r.area or r.city} [{dist}] - Price: {pricing} - Status: {badge}"
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
                reply_msg = await llm.ainvoke(messages)
                return reply_msg.content.strip()
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
        price_info = f" with verified pricing starting at ₹{int(top.price_min)}" if top.price_min else ""
        return (
            f"Namaskara! Found {len(results)} option(s) for your request. "
            f"Top match: {top.name}{dist_info}{price_info}. "
            f"Contact: {top.phone}."
        )

    async def process_chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        """End-to-end processing: parse intent -> call deterministic tools -> synthesize reply."""
        intent, fallback_used = await self.parse_intent(request.message)

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
        )

        return AssistantChatResponse(
            message=request.message,
            intent=intent,
            tool_calls=tool_calls,
            discovery_results=results,
            reply=reply,
            fallback_used=fallback_used,
        )
