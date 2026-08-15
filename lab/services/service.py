from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from common import (
    LAYER_FIELDS,
    anchor_for_slot,
    audit_hash,
    audit_subject_ref,
    build_binding_registry,
    minimize_ai_context,
    pairwise_subject,
    policy_decision,
    random_id,
    resolve_binding,
    sign_token,
    validate_assertion,
    verify_token,
)

MODE = os.environ.get("MODE", "gateway")
PORT = int(os.environ.get("PORT", "8000"))
LAB_AUDIENCE = os.environ.get("LAB_AUDIENCE", "cpims-synthetic-lab")

SESSIONS: dict[str, dict[str, Any]] = {}
ORDERS: dict[str, str] = {}
CONSENTS: dict[str, dict[str, Any]] = {}
ASSERTION_REPLAY: set[str] = set()
DECISION_REPLAY: set[str] = set()
AUDIT_LOCK = threading.Lock()

SLOTS = ["demo-001", "demo-002", "demo-003"]
BINDING_REGISTRY = build_binding_registry(SLOTS)


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


class UpstreamHTTPError(RuntimeError):
    def __init__(self, url: str, status: int, payload: dict[str, Any]):
        self.url = url
        self.status = status
        self.payload = payload
        super().__init__(f"upstream {url} returned {status}: {payload}")


def json_request(url: str, body: dict[str, Any], headers: dict[str, str] | None = None, timeout: float = 3.0) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(detail)
        except json.JSONDecodeError:
            payload = {"error": detail or "upstream-error"}
        raise UpstreamHTTPError(url, exc.code, payload) from exc


def json_get(url: str, timeout: float = 3.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def load_cases() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("data") / "synthetic_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    server_version = "CPIMS-Synthetic-Lab/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{MODE}] {self.address_string()} - {fmt % args}")

    def _send(self, status: int, payload: Any) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 64 * 1024:
            raise ValueError("request too large")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def _session(self) -> tuple[str, dict[str, Any]]:
        token = self.headers.get("X-Session", "")
        session = SESSIONS.get(token)
        if not session or int(session.get("expires_at", 0)) < int(time.time()):
            raise PermissionError("invalid or expired session")
        return token, session

    def do_GET(self) -> None:
        try:
            if self.path == "/health":
                self._send(200, {"status": "ok", "mode": MODE})
                return
            if MODE == "gateway" and self.path == "/api/bootstrap":
                self._send(200, {
                    "name": "CPIMS+ AI Synthetic Lab",
                    "locale": "fa-IR",
                    "synthetic_only": True,
                    "slots": [
                        {"id": "demo-001", "label": "مددجوی مصنوعی ۰۰۱"},
                        {"id": "demo-002", "label": "مددجوی مصنوعی ۰۰۲"},
                        {"id": "demo-003", "label": "مددجوی مصنوعی ۰۰۳"},
                    ],
                    "providers": ["A", "B", "C"],
                    "policy": "2-of-3",
                })
                return
            if MODE == "gateway" and self.path == "/api/audit":
                _, _session = self._session()
                base = env("AUDIT_URL", "http://audit:8000")
                events = json_get(base + "/events")
                verification = json_get(base + "/verify")
                self._send(200, {"events": events.get("events", []), "verification": verification})
                return
            if MODE == "audit" and self.path in {"/events", "/verify"}:
                self._audit_get()
                return
            self._send(404, {"error": "not-found"})
        except PermissionError as exc:
            self._send(401, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": str(exc)})

    def do_POST(self) -> None:
        try:
            body = self._body()
            if MODE == "idp" and self.path == "/attest":
                self._idp_attest(body)
            elif MODE == "oversight" and self.path == "/order":
                self._oversight_order(body)
            elif MODE == "policy" and self.path == "/consent":
                self._policy_consent(body)
            elif MODE == "policy" and self.path == "/revoke":
                self._policy_revoke(body)
            elif MODE == "policy" and self.path == "/authorize":
                self._policy_authorize(body)
            elif MODE == "case" and self.path == "/internal/query":
                self._case_query(body)
            elif MODE == "data_gateway" and self.path == "/fetch":
                self._data_fetch(body)
            elif MODE == "ai" and self.path == "/analyze":
                self._ai_analyze(body)
            elif MODE == "audit" and self.path == "/event":
                self._audit_event(body)
            elif MODE == "gateway":
                self._gateway_post(body)
            else:
                self._send(404, {"error": "not-found"})
        except PermissionError as exc:
            self._send(403, {"error": str(exc)})
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        except UpstreamHTTPError as exc:
            if exc.status in {400, 401, 403, 404, 409}:
                self._send(exc.status, exc.payload)
            else:
                self._send(502, {"error": "upstream-service-error", "status": exc.status})
        except RuntimeError as exc:
            self._send(502, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": str(exc)})

    # ---------- IdP ----------
    def _idp_attest(self, body: dict[str, Any]) -> None:
        provider = env("IDP_ID", "A")
        key = env("IDP_SIGNING_KEY", f"synthetic-idp-{provider}-only")
        slot = str(body.get("slot", ""))
        nonce = str(body.get("nonce", ""))
        audience = str(body.get("audience", ""))
        if slot not in SLOTS or not nonce or audience != LAB_AUDIENCE:
            raise ValueError("invalid synthetic authentication request")
        now = int(time.time())
        payload = {
            "iss": f"synthetic-idp-{provider}",
            "aud": audience,
            "sub": pairwise_subject(provider, slot),
            "nonce": nonce,
            "iat": now,
            "exp": now + 60,
            "jti": random_id("assert"),
            "aal": "synthetic-AAL2-like",
            "synthetic": True,
        }
        self._send(200, {"provider": provider, "assertion": sign_token(payload, key)})

    # ---------- Oversight ----------
    def _oversight_order(self, body: dict[str, Any]) -> None:
        required = ["case_id", "purpose", "requester"]
        if any(not body.get(k) for k in required):
            raise ValueError("case_id, purpose and requester are required")
        if body.get("operation", "read") != "read":
            raise PermissionError("synthetic judicial authority only issues read-scoped orders")
        now = int(time.time())
        order_id = random_id("order")
        payload = {
            "type": "judicial_order",
            "order_id": order_id,
            "case_id": body["case_id"],
            "purpose": body["purpose"],
            "requester": body["requester"],
            "operations": ["read"],
            "iat": now,
            "exp": now + 300,
            "synthetic": True,
        }
        token = sign_token(payload, env("OVERSIGHT_SIGNING_KEY", "synthetic-oversight-only"))
        self._send(200, {"order_id": order_id, "expires_at": payload["exp"], "order_token": token})

    # ---------- Policy ----------
    def _policy_consent(self, body: dict[str, Any]) -> None:
        level = str(body.get("level", ""))
        if level not in {"L2", "L3"}:
            raise ValueError("consent level must be L2 or L3")
        required = ["session_id", "subject_anchor", "purpose"]
        if any(not body.get(k) for k in required):
            raise ValueError("missing consent scope")
        now = int(time.time())
        consent_id = random_id("consent")
        consent = {
            "consent_id": consent_id,
            "session_id": body["session_id"],
            "subject_anchor": body["subject_anchor"],
            "purpose": body["purpose"],
            "level": level,
            "issued_at": now,
            "expires_at": now + 900,
            "revoked": False,
        }
        CONSENTS[body["session_id"]] = consent
        self._send(200, {"consent_id": consent_id, "level": level, "expires_at": consent["expires_at"]})

    def _policy_revoke(self, body: dict[str, Any]) -> None:
        session_id = str(body.get("session_id", ""))
        consent = CONSENTS.get(session_id)
        if not consent:
            raise ValueError("no active consent")
        consent["revoked"] = True
        consent["expires_at"] = 0
        self._send(200, {"revoked": True, "consent_id": consent["consent_id"]})

    def _policy_authorize(self, body: dict[str, Any]) -> None:
        consent = CONSENTS.get(str(body.get("session_id", "")))
        if consent and consent.get("revoked"):
            consent = None

        legal_payload = None
        legal_token = body.get("legal_order")
        if legal_token:
            legal_payload = verify_token(legal_token, env("OVERSIGHT_SIGNING_KEY", "synthetic-oversight-only"))

        allowed, reason, fields = policy_decision(body, consent, legal_payload)
        if not allowed:
            self._send(403, {"allowed": False, "reason": reason})
            return

        now = int(time.time())
        decision_id = random_id("pdd")
        decision = {
            "typ": "policy_decision", "decision_id": decision_id,
            "subject_anchor": body["subject_anchor"],
            "requester_id": body["requester_id"], "requester_role": body["requester_role"],
            "purpose": body["purpose"], "case_id": body["case_id"],
            "layer": body["layer"], "operation": body["operation"],
            "fields": fields, "iat": now, "exp": now + 30,
        }
        self._send(200, {"allowed": True, "reason": reason, "decision_token": sign_token(decision, env("POLICY_SIGNING_KEY", "synthetic-policy-only"))})

    # ---------- Case domain ----------
    def _case_query(self, body: dict[str, Any]) -> None:
        if self.headers.get("X-Lab-Peer-Key") != env("CASE_PEER_KEY", "synthetic-case-peer-only"):
            raise PermissionError("data-gateway peer required")
        subject_anchor = str(body.get("subject_anchor", ""))
        case_id = str(body.get("case_id", ""))
        fields = list(body.get("fields", []))
        records = load_cases()
        if body.get("list_mode"):
            rows = [{k: r.get(k) for k in fields} for r in records if r["subject_anchor"] == subject_anchor]
            self._send(200, {"records": rows})
            return

        record = next((r for r in records if r["subject_anchor"] == subject_anchor and r["case_id"] == case_id), None)
        if not record:
            self._send(404, {"error": "synthetic case not found"})
            return
        self._send(200, {"case": {k: record.get(k) for k in fields}})

    # ---------- Data Gateway / PEP ----------
    def _data_fetch(self, body: dict[str, Any]) -> None:
        decision_token = str(body.get("decision_token", ""))
        decision = verify_token(decision_token, env("POLICY_SIGNING_KEY", "synthetic-policy-only"))
        jti = str(decision.get("decision_id", ""))
        if not jti or jti in DECISION_REPLAY:
            raise PermissionError("decision token replay")
        DECISION_REPLAY.add(jti)

        query = {
            "subject_anchor": decision["subject_anchor"],
            "case_id": decision["case_id"],
            "fields": decision["fields"],
            "list_mode": decision["operation"] == "list",
        }
        response = json_request(env("CASE_URL", "http://case:8000") + "/internal/query", query, headers={"X-Lab-Peer-Key": env("CASE_PEER_KEY", "synthetic-case-peer-only")})
        self._send(200, response)

    # ---------- AI ----------
    def _ai_analyze(self, body: dict[str, Any]) -> None:
        decision_token = str(body.get("decision_token", ""))
        # AI cannot call the case domain. It can only consume a short-lived PDP decision via the PEP.
        response = json_request(env("DATA_GATEWAY_URL", "http://data-gateway:8000") + "/fetch", {"decision_token": decision_token})
        context = response.get("case", {})
        context = minimize_ai_context(context)

        missing = []
        for key in ("family_structure", "social_summary"):
            if not context.get(key):
                missing.append(key)

        flags = context.get("safeguarding_flags") or []
        if missing:
            recommendation = "insufficient_evidence"
            confidence = "low"
            uncertainty = "اطلاعات ن اديكافاف برای نتیجه نهایی كافی است."
        elif flags :
            recommendation = "human_safeguarding_review_required"
            confidence = "low"
            uncertainty = "پر؆ده بايم سازعدند پةیشین الزامات است"
        else:
            recommendation = "consider_continued_human_assessment"
            confidence = "medium"
            uncertainty = "ێین ؾیشنهاد تصمیم نهایی نجام ن ن ناعملاف است."

        self._send(200, {
            "ai_context_id": random_id("aictx"),
            "model_version": "synthetic-rule-engine-0.1",
            "evidence": context,
            "recommendation": recommendation,
            "confidence": confidence,
            "uncertainty": uncertainty,
            "missing_evidence": missing,
            "alternative_explanation": "این خروجی فقط بی اطلاعات ن نياز ارٲایؤی است و تجمیع نهایی باید سایر شواهد يدباره بررسی شود.",
            "decision_authority": False,
            "abstain_supported": True,
        })

    # ---------- Audit ----------
    def _audit_path(self) -> Path:
        return Path(env("AUDIT_FILE", "/tmp/audit.jsonl"))

    def _read_audit(self) -> list[dict[str, Any]]:
        path = self._audit_path()
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _audit_event(self, body: dict[str, Any]) -> None:
        if not body.get("action"):
            raise ValueError("audit action required")
        with AUDIT_LOCK:
            existing = self._read_audit()
            previous = existing[-1]["hash"] if existing else "GENESIS"
            event = dict(body)
            event["seq"] = len(existing) + 1
            event["timestamp"] = int(time.time())
            digest = audit_hash(previous, event)
            record = {"previous_hash": previous, **event, "hash": digest}
            path = self._audit_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        self._send(201, {"accepted": True, "seq": record["seq"], "hash": digest})

    def _audit_get(self) -> None:
        items = self._read_audit()
        if self.path == "/events":
            self._send(200, {"events": items[-50:]})
            return
        previous = "GENESIS"
        valid = True
        failed_seq = None
        for record in items:
            core = {k: v for k, v in record.items() if k not in {"hash", "previous_hash"}}
            expected = audit_hash(previous, core)
            if record.get("previous_hash") != previous or record.get("hash") != expected:
                valid = False
                failed_seq = record.get("seq")
                break
            previous = str(record["hash"])
        self._send(200, {"valid": valid, "records": len(items), "failed_seq": failed_seq})

    # ---------- Gateway ----------
    def _audit(self, event: dict[str, Any]) -> None:
        try:
            json_request(env("AUDIT_URL", "http://audit:8000") + "/event", event)
        except Exception as exc:
            # In this lab sensitive actions fail closed when audit is unavailable.
            raise RuntimeError(f"audit unavailable: {exc}") from exc

    def _gateway_post(self, body: dict[str, Any]) -> None:
        path = self.path
        if path == "/api/authenticate":
            slot = str(body.get("slot", ""))
            if slot not in SLOTS:
                raise ValueError("unknown synthetic subject")
            skip = str(body.get("skip_provider", "")).upper()
            nonce = random_id("nonce")
            idps = {
                "A": (env("IDP_A_URL", "http://idp-a:8000"), env("IDP_A_KEY", "synthetic-idp-A-only")),
                "B": (env("IDP_B_URL", "http://idp-b:8000"), env("IDP_B_KEY", "synthetic-idp-B-only")),
                "C": (env("IDP_C_URL", "http://idp-c:8000"), env("IDP_C_KEY", "synthetic-idp-C-only")),
            }
            validated = []
            providers = []
            for provider, (url, key) in idps.items():
                if provider == skip:
                    continue
                try:
                    response = json_request(url + "/attest", {"slot": slot, "nonce": nonce, "audience": LAB_AUDIENCE}, timeout=2.0)
                    payload = validate_assertion(
                        response["assertion"], key, f"synthetic-idp-{provider}", LAB_AUDIENCE, nonce, ASSERTION_REPLAY
                    )
                    validated.append(payload)
                    providers.append(provider)
                except Exception:
                    continue
            if len(validated) < 2:
                raise PermissionError("2-of-3 identity threshold not satisfied")
            anchor = resolve_binding(validated, BINDING_REGISTRY)
            session_token = random_id("session")
            session_id = random_id("sid")
            SESSIONS[session_token] = {
                "session_id": session_id,
                "subject_anchor": anchor,
                "slot": slot,
                "requester_id": "worker-demo-01",
                "requester_role": "social_worker",
                "expires_at": int(time.time()) + 600,
            }
            self._audit({
                "actor_ref": "worker-demo-01",
                "subject_ref": audit_subject_ref(anchor, env("AUDIT_PSEUDO_KEY", "synthetic-audit-pseudonym-only")),
                "action": "identity_session_created",
                "purpose": "case-support",
                "providers": providers,
                "result": "2-of-3-satisfied",
            })
            self._send(200, {"session": session_token, "expires_in": 600, "providers": providers, "threshold": "2-of-3"})
            return

        session_token, session = self._session()
        purpose = str(body.get("purpose", "family_reunification"))
        subject_ref = audit_subject_ref(session["subject_anchor"], env("AUDIT_PSEUDO_KEY", "synthetic-audit-pseudonym-only"))

        if path == "/api/consent":
            level = str(body.get("level", "L2"))
            response = json_request(env("POLICY_URL", "http://policy:8000") + "/consent", {
                "session_id": session["session_id"],
                "subject_anchor": session["subject_anchor"],
                "purpose": purpose,
                "level": level,
            })
            self._audit({"actor_ref": session["requester_id"], "subject_ref": subject_ref, "action": "consent_recorded", "purpose": purpose, "layer": level})
            self._send(200, response)
            return

        if path == "/api/revoke-consent":
            response = json_request(env("POLICY_URL", "http://policy:8000") + "/revoke", {"session_id": session["session_id"]})
            self._audit({"actor_ref": session["requester_id"], "subject_ref": subject_ref, "action": "consent_revoked", "purpose": purpose})
            self._send(200, response)
            return

        if path == "/api/cases":
            decision = self._policy_request(session, purpose, "*", "L1", "list", None)
            records = json_request(env("DATA_GATEWAY_URL", "http://data-gateway:8000") + "/fetch", {"decision_token": decision})
            self._audit({"actor_ref": session["requester_id"], "subject_ref": subject_ref, "action": "case_list_read", "purpose": purpose, "layer": "L1"})
            self._send(200, records)
            return

        if path == "/api/mock-judicial-order":
            case_id = str(body.get("case_id", ""))
            response = json_request(env("OVERSIGHT_URL", "http://oversight:8000") + "/order", {
                "case_id": case_id,
                "purpose": purpose,
                "requester": session["requester_id"],
                "operation": "read",
            })
            ORDERS[response["order_id"]] = response["order_token"]
            self._audit({"actor_ref": "synthetic-judicial-authority", "subject_ref": subject_ref, "action": "l4_order_issued", "purpose": purpose, "case_ref": case_id, "order_ref": response["order_id"]})
            self._send(200, {"order_id": response["order_id"], "expires_at": response["expires_at"], "scope": "L4 read only"})
            return

        if path == "/api/case":
            case_id = str(body.get("case_id", ""))
            layer = str(body.get("layer", "L1"))
            order_token = ORDERS.get(str(body.get("order_id", ""))) if layer == "L4" else None
            decision = self._policy_request(session, purpose, case_id, layer, "read", order_token)
            record = json_request(env("DATA_GATEWAY_URL", "http://data-gateway:8000") + "/fetch", {"decision_token": decision})
            self._audit({"actor_ref": session["requester_id"], "subject_ref": subject_ref, "action": "case_layer_read", "purpose": purpose, "case_ref": case_id, "layer": layer})
            self._send(200, record)
            return

        if path == "/api/analyze":
            case_id = str(body.get("case_id", ""))
            layer = str(body.get("layer", "L2"))
            if layer not in {"L2", "L3"}:
                raise ValueError("AI context is limited to L2/L3 in the lab")
            decision = self._policy_request(session, purpose, case_id, layer, "ai_context", None)
            analysis = json_request(env("AI_URL", "http://ai:8000") + "/analyze", {"decision_token": decision})
            self._audit({"actor_ref": session["requester_id"], "subject_ref": subject_ref, "action": "ai_assistance_requested", "purpose": purpose, "case_ref": case_id, "layer": layer, "model_version": analysis.get("model_version")})
            self._send(200, analysis)
            return

        if path == "/api/decision":
            case_id = str(body.get("case_id", ""))
            outcome = str(body.get("outcome", ""))
            allowed_outcomes = {"consider_reunification", "follow_up", "do_not_reunify_yet", "insufficient_evidence"}
            if outcome not in allowed_outcomes:
                raise ValueError("invalid synthetic human decision")
            reason = str(body.get("reason", ""))[:500]
            self._audit({
                "actor_ref": session["requester_id"], "subject_ref": subject_ref,
                "action": "human_decision_recorded", "purpose": purpose, "case_ref": case_id,
                "human_decision": outcome, "reason": reason,
            })
            self._send(200, {"recorded": True, "human_decision": outcome, "ai_has_decision_authority": False})
            return

        self._send(404, {"error": "not-found"})

    def _policy_request(self, session: dict[str, Any], purpose: str, case_id: str, layer: str, operation: str, legal_order: str | None) -> str:
        response = json_request(env("POLICY_URL", "http://policy:8000") + "/authorize", {
            "session_id": session["session_id"],
            "subject_anchor": session["subject_anchor"],
            "requester_id": session["requester_id"],
            "requester_role": session["requester_role"],
            "purpose": purpose,
            "case_id": case_id,
            "layer": layer,
            "operation": operation,
            "legal_order": legal_order,
        })
        if not response.get("allowed"):
            raise PermissionError(response.get("reason", "policy denied"))
        return str(response["decision_token"])


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Starting mode={MODE} on :{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
