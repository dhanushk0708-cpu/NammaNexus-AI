import logging
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_current_admin(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """Verifies that the requester is an authorized platform administrator.

    Checks 'X-Admin-Token', 'X-API-Key', or 'Authorization: Bearer <token>'.
    Uses constant-time comparison against configured admin tokens.
    """
    token: str | None = None
    if x_admin_token and x_admin_token.strip():
        token = x_admin_token.strip()
    elif x_api_key and x_api_key.strip():
        token = x_api_key.strip()
    elif authorization and authorization.strip():
        parts = authorization.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip() or None
        elif len(parts) == 1 and parts[0].lower() != "bearer":
            token = parts[0].strip() or None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authorization token is required. Pass 'X-Admin-Token' or 'Authorization: Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Configured tokens
    valid_tokens = [
        t for t in [settings.nammadeals_admin_token, settings.civicvoice_api_token]
        if t and t.strip()
    ]
    # In development/test environments, allow the standard dev secret token if configured or fallback
    if settings.environment in ("development", "test"):
        valid_tokens.append("test-nammadeals-admin-secret-token")

    if not valid_tokens:
        logger.error("No admin API token configured on server (NAMMADEALS_ADMIN_TOKEN or CIVICVOICE_API_TOKEN).")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is locked. Server admin token is not configured.",
        )

    matched = any(secrets.compare_digest(token, expected) for expected in valid_tokens)
    if not matched:
        logger.warning("Invalid admin token attempt.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin credentials.",
        )

    return "admin"


def get_current_user(
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    """Identifies the authenticated business owner / citizen user.

    In the current architecture, external user identities are passed via
    'X-User-ID' header or parsed from 'Authorization: Bearer <user_id_or_token>'.
    """
    user_id: str | None = None
    if x_user_id and x_user_id.strip():
        user_id = x_user_id.strip()
    elif authorization and authorization.strip():
        parts = authorization.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token_val = parts[1].strip()
            # If token starts with user_, use it as user ID
            if token_val.startswith("user_") or token_val.startswith("usr_"):
                user_id = token_val
            elif token_val:
                user_id = token_val

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide 'X-User-ID' header or valid Bearer credentials.",
        )

    return user_id
