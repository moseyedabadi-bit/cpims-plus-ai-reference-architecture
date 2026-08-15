"""CPIMS+ security reference implementation (synthetic PoC only).

This module deliberately has no web framework or database dependency. It models
security properties that a real Primero/CPIMS+ integration can enforce at the
edge: 2-of-3 identity attestations, pairwise pseudonymous identifiers,
purpose-bound consent/authorization, AI context minimization, and tamper-evident
audit chaining.

It is NOT production authentication software and does not replace a certified
OIDC/FIDO/WebAuthn implementation, HSM/KMS, independent legal review, or the
Primero security model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import base64
import hmac
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

UTC = timezone.utc


class SecurityError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise SecurityError("invalid timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def sign_assertion(payload: Mapping[str, Any], secret: bytes) -> str:
    """PoC MAC assertion. Production federation should use vetted protocols/libraries."""
    body = _b64u(_canonical_json(payload))
    mac = hmac.new(secret, body.encode("ascii"), sha256).digest()
    return f"{body}.{_b64u(mac)}"


def decode_and_verify_assertion(token: str, secret: bytes) -> dict[str, Any]:
    try:
        body, encoded_mac = token.split(".", 1)
    except ValueError as exc:
        raise SecurityError("malformed assertion") from exc
    expected = hmac.new(secret, body.encode("ascii"), sha256).digest()
    supplied = _b64u_decode(encoded_mac)
    if not hmac.compare_digest(expected, supplied):
        raise SecurityError("invalid assertion signature")
    try:
        data = json.loads(_b64u_decode(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise SecurityError("invalid assertion payload") from exc
    if not isinstance(data, dict):
        raise SecurityError("assertion payload must be an object")
    return data


@dataclass(frozen=True)
class Provider:
    issuer: str
    secret: bytes


@dataclass
class ReplayCache:
    seen: dict[str, datetime] = field(default_factory=dict)

    def consume(self, assertion_id: str, expires_at: datetime, now: datetime) -> None:
        self.seen = {key: exp for key, exp in self.seen.items() if exp > now}
        if assertion_id in self.seen:
            raise SecurityError("assertion replay detected")
        self.seen[assertion_id] = expires_at


@dataclass
class SubjectBindingRegistry:
    """Private mapping. Providers never receive the internal subject anchor."""

    bindings: Mapping[tuple[str, str], str]

    def resolve(self, issuer: str, subject: str) -> str:
        try:
            return self.bindings[(issuer, subject)]
        except KeyError as exc:
            raise SecurityError("unknown subject binding") from exc


@dataclass(frozen=True)
class Session:
    token_hash: str
    subject_anchor: str
    issued_at: datetime
    expires_at: datetime
    assurance: str


class TrustGateway:
    """Require at least two valid, distinct, mutually-bound provider assertions."""

    def __init__(
        self,
        providers: Iterable[Provider],
        registry: SubjectBindingRegistry,
        audience: str = "cpims-plus",
        assertion_max_ttl_seconds: int = 300,
        session_ttl_seconds: int = 1800,
    ) -> None:
        self.providers = {provider.issuer: provider for provider in providers}
        if len(self.providers) < 3:
            raise ValueError("reference design expects at least three independent providers")
        self.registry = registry
        self.audience = audience
        self.assertion_max_ttl = timedelta(seconds=assertion_max_ttl_seconds)
        self.session_ttl = timedelta(seconds=session_ttl_seconds)
        self.replay = ReplayCache()
        self.sessions: dict[str, Session] = {}

    def _verify_one(self, token: str, expected_nonce: str, now: datetime) -> tuple[str, str, str]:
        try:
            body = token.split(".", 1)[0]
            untrusted = json.loads(_b64u_decode(body))
            issuer = untrusted["iss"]
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise SecurityError("cannot select assertion issuer") from exc
        provider = self.providers.get(issuer)
        if provider is None:
            raise SecurityError("untrusted issuer")
        data = decode_and_verify_assertion(token, provider.secret)
        required = {"iss", "aud", "iat", "exp", "jti", "auth_time", "sub", "nonce"}
        if not required.issubset(data):
            raise SecurityError("assertion missing required claims")
        if data["iss"] != issuer or data["aud"] != self.audience:
            raise SecurityError("issuer/audience mismatch")
        if data["nonce"] != expected_nonce:
            raise SecurityError("nonce mismatch")
        issued_at = _parse_time(data["iat"])
        expires_at = _parse_time(data["exp"])
        auth_time = _parse_time(data["auth_time"])
        if issued_at > now + timedelta(seconds=60):
            raise SecurityError("assertion issued in the future")
        if expires_at <= now or expires_at - issued_at > self.assertion_max_ttl:
            raise SecurityError("assertion expired or TTL too long")
        if auth_time > issued_at + timedelta(seconds=60):
            raise SecurityError("invalid authentication time")
        assertion_id = str(data["jti"])
        self.replay.consume(assertion_id, expires_at, now)
        subject = str(data["sub"])
        if any(marker in subject.lower() for marker in ("@", "mailto:", "phone:")):
            raise SecurityError("subject identifier appears directly identifying")
        anchor = self.registry.resolve(issuer, subject)
        return issuer, subject, anchor

    def establish_session(self, assertions: Iterable[str], nonce: str, now: datetime | None = None) -> tuple[str, Session]:
        current = now or _now()
        tokens = list(assertions)
        if len(tokens) < 2 or len(tokens) > 3:
            raise SecurityError("2-of-3 policy requires two or three assertions")
        verified = [self._verify_one(token, nonce, current) for token in tokens]
        issuers = {item[0] for item in verified}
        if len(issuers) < 2:
            raise SecurityError("two distinct providers are required")
        anchors = {item[2] for item in verified}
        if len(anchors) != 1:
            raise SecurityError("provider assertions do not resolve to the same subject")
        token = secrets.token_urlsafe(32)
        token_hash = sha256(token.encode("utf-8")).hexdigest()
        session = Session(
            token_hash=token_hash,
            subject_anchor=anchors.pop(),
            issued_at=current,
            expires_at=current + self.session_ttl,
            assurance="project-2-of-3",
        )
        self.sessions[token_hash] = session
        return token, session

    def verify_session(self, token: str, now: datetime | None = None) -> Session:
        current = now or _now()
        token_hash = sha256(token.encode("utf-8")).hexdigest()
        session = self.sessions.get(token_hash)
        if session is None or session.expires_at <= current:
            raise SecurityError("invalid or expired session")
        return session


def derive_pairwise_id(subject_anchor: str, domain: str, domain_key: bytes) -> str:
    """Keyed, domain-scoped pseudonym. Never use a raw national identifier as input here."""
    if not domain or len(domain_key) < 32:
        raise ValueError("domain and >=256-bit domain key required")
    digest = hmac.new(domain_key, f"{domain}\0{subject_anchor}".encode("utf-8"), sha256).digest()
    return f"ppi_{domain}_{_b64u(digest[:18])}"


@dataclass
class ConsentReceipt:
    receipt_id: str
    subject_anchor: str
    requester_id: str
    purpose: str
    max_layer: int
    issued_at: datetime
    expires_at: datetime
    step_up: bool = False
    revoked: bool = False

    def valid_for(self, subject_anchor: str, requester_id: str, purpose: str, layer: int, now: datetime) -> bool:
        return (
            not self.revoked
            and self.subject_anchor == subject_anchor
            and self.requester_id == requester_id
            and self.purpose == purpose
            and self.max_layer >= layer
            and self.issued_at <= now < self.expires_at
            and (layer < 3 or self.step_up)
        )


@dataclass(frozen=True)
class AuthorizationGrant:
    grant_id: str
    grant_type: str
    subject_anchor: str
    requester_id: str
    purpose: str
    data_layers: frozenset[int]
    operations: frozenset[str]
    issued_by: str
    issued_at: datetime
    expires_at: datetime
    legal_basis: str
    reason_code: str
    requires_post_review: bool = False

    def valid_for(self, subject_anchor: str, requester_id: str, purpose: str, layer: int, operation: str, now: datetime) -> bool:
        return (
            self.subject_anchor == subject_anchor
            and self.requester_id == requester_id
            and self.purpose == purpose
            and layer in self.data_layers
            and operation in self.operations
            and self.issued_at <= now < self.expires_at
        )


@dataclass(frozen=True)
class AccessRequest:
    actor_role: str
    requester_id: str
    subject_anchor: str
    assigned_to_case: bool
    purpose: str
    layer: int
    operation: str = "read"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    """Reference policy; local law and safeguarding policy must be reviewed before deployment."""

    PROFESSIONAL_ROLES = frozenset({"social_worker", "supervisor"})
    LEGAL_GRANT_TYPES = frozenset({"judicial_order", "statutory_duty", "safeguarding_emergency"})

    def evaluate(
        self,
        request: AccessRequest,
        consent: ConsentReceipt | None = None,
        grant: AuthorizationGrant | None = None,
        now: datetime | None = None,
    ) -> PolicyDecision:
        current = now or _now()
        if request.layer not in {1, 2, 3, 4}:
            return PolicyDecision(False, "unknown data layer")
        if request.actor_role not in self.PROFESSIONAL_ROLES:
            return PolicyDecision(False, "role has no routine case-data authority")
        if not request.assigned_to_case:
            return PolicyDecision(False, "requester is not assigned to this case")
        if request.operation not in {"read"}:
            return PolicyDecision(False, "operation is not allowed by this reference policy")
        if request.layer == 1:
            return PolicyDecision(True, "L1 assignment-scoped access")
        consent_ok = consent is not None and consent.valid_for(
            request.subject_anchor, request.requester_id, request.purpose, request.layer, current
        )
        if request.layer in {2, 3}:
            return PolicyDecision(consent_ok, "valid purpose-bound consent" if consent_ok else "consent/step-up requirements not met")
        grant_ok = (
            grant is not None
            and grant.grant_type in self.LEGAL_GRANT_TYPES
            and grant.valid_for(
                request.subject_anchor,
                request.requester_id,
                request.purpose,
                request.layer,
                request.operation,
                current,
            )
        )
        return PolicyDecision(grant_ok, "valid scoped legal/emergency grant" if grant_ok else "L4 requires scoped legal/emergency grant")


def emergency_grant(
    *,
    subject_anchor: str,
    requester_id: str,
    purpose: str,
    layer: int,
    issued_by: str,
    reason_code: str,
    now: datetime | None = None,
) -> AuthorizationGrant:
    if not reason_code.strip():
        raise SecurityError("break-glass requires a reason")
    current = now or _now()
    return AuthorizationGrant(
        grant_id=f"emg_{secrets.token_urlsafe(12)}",
        grant_type="safeguarding_emergency",
        subject_anchor=subject_anchor,
        requester_id=requester_id,
        purpose=purpose,
        data_layers=frozenset({layer}),
        operations=frozenset({"read"}),
        issued_by=issued_by,
        issued_at=current,
        expires_at=current + timedelta(minutes=15),
        legal_basis="emergency_safeguarding_policy",
        reason_code=reason_code,
        requires_post_review=True,
    )


class AIContextBuilder:
    """Build an ephemeral minimum-necessary envelope; identity fields are rejected."""

    FORBIDDEN_FIELDS = frozenset(
        {
            "name", "full_name", "national_id", "passport", "phone", "email",
            "exact_address", "biometric", "biometric_template", "case_anchor", "identity_token",
        }
    )

    def build(self, case: Mapping[str, Any], purpose: str, ttl_seconds: int = 120) -> dict[str, Any]:
        lowered = {str(key).lower() for key in case}
        leaked = lowered & self.FORBIDDEN_FIELDS
        if leaked:
            raise SecurityError(f"raw identity fields supplied to AI context builder: {sorted(leaked)}")
        age = case.get("age")
        age_group = self._age_group(age) if isinstance(age, int) else "unknown"
        current = _now()
        return {
            "ai_ctx": f"aictx_{secrets.token_urlsafe(18)}",
            "purpose": purpose,
            "expires_at": _iso(current + timedelta(seconds=min(max(ttl_seconds, 30), 300))),
            "age_group": age_group,
            "case_status": case.get("case_status"),
            "coarse_region": case.get("coarse_region"),
            "family_relation": case.get("family_relation"),
            "evidence": list(case.get("evidence", []))[:20],
            "missing_evidence": list(case.get("missing_evidence", []))[:20],
        }

    @staticmethod
    def _age_group(age: int) -> str:
        if age < 0:
            return "unknown"
        if age <= 5:
            return "0-5"
        if age <= 9:
            return "6-9"
        if age <= 12:
            return "10-12"
        if age <= 15:
            return "13-15"
        if age <= 17:
            return "16-17"
        return "18+"


class AuditChain:
    """Tamper-evident local chain for PoC. Production audit must be independently administered."""

    def __init__(self, path: str | Path, integrity_key: bytes) -> None:
        if len(integrity_key) < 32:
            raise ValueError("audit integrity key must be >=256 bits")
        self.path = Path(path)
        self.key = integrity_key

    def append(self, event: Mapping[str, Any]) -> str:
        forbidden = {"name", "national_id", "phone", "email", "exact_address", "biometric"}
        if forbidden & {str(key).lower() for key in event}:
            raise SecurityError("direct identity data is forbidden in audit events")
        previous = self._last_hash()
        payload = {"event": dict(event), "prev_hash": previous, "ts": _iso(_now())}
        event_hash = hmac.new(self.key, _canonical_json(payload), sha256).hexdigest()
        record = {**payload, "hash": event_hash}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return event_hash

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return "GENESIS"
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return "GENESIS"
        return json.loads(lines[-1])["hash"]

    def verify(self) -> bool:
        if not self.path.exists():
            return True
        previous = "GENESIS"
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                supplied = record.pop("hash")
                if record.get("prev_hash") != previous:
                    return False
                expected = hmac.new(self.key, _canonical_json(record), sha256).hexdigest()
                if not hmac.compare_digest(expected, supplied):
                    return False
                previous = supplied
        return True
