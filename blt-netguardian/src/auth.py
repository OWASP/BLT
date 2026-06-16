"""Org-scoped API token auth for triage routes."""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass
class OrgAuthContext:
    org_id: str
    token: str


class AuthError(Exception):
    def __init__(self, message: str, *, status: int = 401) -> None:
        self.message = message
        self.status = status
        super().__init__(message)

    def to_response_body(self) -> dict:
        return {"error": "unauthorized", "message": self.message}


def extract_bearer_token(headers: Mapping[str, str]) -> Optional[str]:
    authorization = headers.get("Authorization") or headers.get("authorization")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _load_org_token_map(env: Any) -> dict[str, str]:
    raw = getattr(env, "NG_ORG_API_TOKENS", None)
    if not raw:
        return {}
    try:
        mapping = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    if not isinstance(mapping, dict):
        return {}
    result: dict[str, str] = {}
    for token, org_id in mapping.items():
        if token and org_id:
            result[str(token)] = str(org_id)
    return result


def resolve_org_from_token(env: Any, token: str) -> Optional[str]:
    """Map Bearer token to org_id using NG_ORG_API_TOKENS JSON."""
    if not token:
        return None
    for configured_token, org_id in _load_org_token_map(env).items():
        if hmac.compare_digest(configured_token, token):
            return org_id
    return None


def require_org_auth(env: Any, headers: Mapping[str, str]) -> OrgAuthContext:
    token = extract_bearer_token(headers)
    if not token:
        raise AuthError("missing Bearer token")
    org_id = resolve_org_from_token(env, token)
    if org_id is None:
        raise AuthError("invalid or unknown API token")
    return OrgAuthContext(org_id=org_id, token=token)
