from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

LAYER_NUM = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}

LAYER_FIELDS = {
    "L1": ["case_id", "case_alias", "age_band", "case_status", "province_band"],
    "L2": [
        "case_alias", "age_band", "case_status", "province_band",
        "family_structure", "social_summary", "reunification_goal",
    ],
    "L3": [
        "case_alias", "age_band", "case_status", "province_band",
        "family_structure", "social_summary", "reunification_goal",
        "safeguarding_flags", "health_summary",
    ],
    "L4": [
        "case_alias", "age_band", "case_status", "province_band",
        "family_structure", "social_summary", "reunification_goal",
        "safeguarding_flags", "health_summary", "sealed_note",
    ],
}

FORBIDDEN_AI_KEYS = {
    "name", "full_name", "national_id", "national_code", "phone", "mobile",
    "email", "exact_address", "address", "biometric", "biometric_template",
    "identity_anchor", "subject_anchor", "case_anchor", "raw_identity",
}


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_token(payload: dict[str, Any], key: str) -> str:
    encoded = b64u(canonical_json(payload))
    sig = hmac.new(key.encode(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{b64u(sig)}"


def verify_token(token: str, key: str, now: int | None = None) -> dict[str, Any]:
    try:
        encoded, supplied_sig = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("malformed token") from exc
    expected = hmac.new(key.encode(), encoded.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(b64u(expected), supplied_sig):
        raise ValueError("invalid signature")
    payload = json.loads(b64u_decode(encoded))
    now = int(time.time()) if now is None else now
    if "exp" in payload and int(payload["exp"]) < now:
        raise ValueError("expired token")
    if "nbf" in payload and int(payload["nbf"]) > now:
        raise ValueError("token not active")
    return payload


def pairwise_subject(provider_id: str, slot: str) -> str:
    # Synthetic-lab pseudonym only. Production IdPs must issue their own opaque PPIs.
    digest = hashlib.sha256(f"synthetic-lab:{provider_id}:{slot}".encode()).hexdigest()[:20]
    return f"ppi-{provider_id.lower()}-{digest}"


def anchor_for_slot(slot: str) -> str:
    digest = hashlib.sha256(f"synthetic-anchor:{slot}".encode()).hexdigest()[:24]
    return f"subject-{digest}"


def build_binding_registry(slots: list[str]) -> dict[str, str]:
    registry: dict[str, str] = {}
    for slot in slots:
        anchor = anchor_for_slot(slot)
        for provider in ("A", "B", "C"):
            registry[pairwise_subject(provider, slot)] = anchor
    return registry


def validate_assertion(
    token: str,
    key: str,
    expected_issuer: str,
    audience: str,
    nonce: str,
    replay_cache: set[str],
    now: int | None = None,
) -> dict[str, Any]:
    now = int(time.time()) if now is None else now
    payload = verify_token(token, key, now)
    if payload.get("iss") != expected_issuer:
        raise ValueError("wrong issuer")
    if payload.get("aud") != audience:
        raise ValueError("wrong audience")
    if payload.get("nonce") != nonce:
        raise ValueError("wrong nonce")
    iat = int(payload.get("iat", 0))
    if abs(now - iat) > 120:
        raise ValueError("stale assertion")
    jti = str(payload.get("jti", ""))
    if not jti or jti in replay_cache:
        raise ValueError("assertion replay")
    replay_cache.add(jti)
    if not payload.get("sub"):
        raise ValueError("missing subject")
    return payload


def resolve_binding(assertions: list[dict[str, Any]], registry: dict[str, str]) -> str:
    anchors = {registry.get(str(item.get("sub"))) for item in assertions}
    if None in anchors or len(anchors) != 1:
        raise ValueError("cross-provider subject binding failed")
    return anchors.pop()  # type: ignore[return-value]


def level_at_least(granted: str, requested: str) -> bool:
    return LAYER_NUM.get(granted, 0) >= LAYER_NUM.get(requested, 99)


def policy_decision(
    request: dict[str, Any],
    consent: dict[str, Any] | None,
    legal_order: dict[str, Any] | None,
    now: int | None = None,
) -> tuple[bool, str, list[str]]:
    now = int(time.time()) if now is None else now
    role = request.get("requester_role")
    layer = str(request.get("layer", ""))
    operation = request.get("operation")
    purpose = request.get("purpose")

    if role != "social_worker":
        return False, "requester-role-denied", []
    if layer not in LAYER_NUM:
        return False, "invalid-layer", []
    if operation in {"export", "bulk_export"}:
        return False, "bulk-export-denied", []
    if operation == "list" and layer != "L1":
        return False, "list-only-l1", []
    if operation == "ai_context" and layer == "L4":
        return False, "ai-l4-denied", []

    if layer in {"L2", "L3", "L4"}:
        if not consent:
            return False, "consent-required", []
        if consent.get("session_id") != request.get("session_id"):
            return False, "consent-session-mismatch", []
        if consent.get("subject_anchor") != request.get("subject_anchor"):
            return False, "consent-subject-mismatch", []
        if consent.get("purpose") != purpose:
            return False, "consent-purpose-mismatch", []
        if int(consent.get("expires_at", 0)) < now:
            return False, "consent-expired", []
        consent_threshold = "L3" if layer == "L4" else layer
        if not level_at_least(str(consent.get("level")), consent_threshold):
            return False, "step-up-consent-required", []

    if layer == "L4":
        if not legal_order:
            return False, "independent-legal-authorization-required", []
        if legal_order.get("type") not in {"judicial_order", "statutory_duty", "safeguarding_emergency"}:
            return False, "invalid-legal-basis", []
        if legal_order.get("case_id") != request.get("case_id"):
            return False, "order-case-mismatch", []
        if legal_order.get("purpose") != purpose:
            return False, "order-purpose-mismatch", []
        if legal_order.get("requester") != request.get("requester_id"):
            return False, "order-requester-mismatch", []
        if operation not in legal_order.get("operations", []):
            return False, "order-operation-denied", []
        if int(legal_order.get("exp", 0)) < now:
            return False, "order-expired", []

    return True, "allow", list(LAYER_FIELDS[layer])


def minimize_ai_context(record: dict[str, Any]) -> dict[str, Any]:
    lowered = {str(k).lower() for k in record}
    blocked = lowered.intersection(FORBIDDEN_AI_KEYS)
    if blocked:
        raise ValueError(f"identity-like fields rejected from AI context: {sorted(blocked)}")

    allowed = {
        "case_alias", "age_band", "case_status", "province_band",
        "family_structure", "social_summary", "reunification_goal",
        "safeguarding_flags", "health_summary",
    }
    return {k: v for k, v in record.items() if k in allowed}


def audit_subject_ref(anchor: str, key: str) -> str:
    return "aud-" + hmac.new(key.encode(), anchor.encode(), hashlib.sha256).hexdigest()[:20]


def audit_hash(previous_hash: str, event: dict[str, Any]) -> str:
    material = previous_hash.encode() + b"|" + canonical_json(event)
    return hashlib.sha256(material).hexdigest()


def random_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_urlsafe(12)}"
