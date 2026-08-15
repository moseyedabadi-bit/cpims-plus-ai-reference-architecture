import sys
import time
import unittest
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[1] / "services"
sys.path.insert(0, str(SERVICES))

from common import (  # noqa: E402
    anchor_for_slot,
    audit_hash,
    build_binding_registry,
    minimize_ai_context,
    pairwise_subject,
    policy_decision,
    resolve_binding,
    sign_token,
    validate_assertion,
)


class SyntheticLabTests(unittest.TestCase):
    def setUp(self):
        self.now = int(time.time())
        self.audience = "cpims-synthetic-lab"
        self.nonce = "nonce-1"
        self.registry = build_binding_registry(["demo-001", "demo-002"])

    def assertion(self, provider: str, slot: str, jti: str):
        key = f"key-{provider}"
        payload = {
            "iss": f"synthetic-idp-{provider}",
            "aud": self.audience,
            "sub": pairwise_subject(provider, slot),
            "nonce": self.nonce,
            "iat": self.now,
            "exp": self.now + 60,
            "jti": jti,
        }
        return sign_token(payload, key), key

    def test_two_independent_assertions_bind_to_one_subject(self):
        replay = set()
        validated = []
        for p in ("A", "B"):
            token, key = self.assertion(p, "demo-001", f"jti-{p}")
            validated.append(validate_assertion(token, key, f"synthetic-idp-{p}", self.audience, self.nonce, replay, self.now))
        self.assertEqual(resolve_binding(validated, self.registry), anchor_for_slot("demo-001"))

    def test_cross_subject_binding_is_rejected(self):
        replay = set()
        a, key_a = self.assertion("A", "demo-001", "jti-a")
        b, key_b = self.assertion("B", "demo-002", "jti-b")
        validated = [
            validate_assertion(a, key_a, "synthetic-idp-A", self.audience, self.nonce, replay, self.now),
            validate_assertion(b, key_b, "synthetic-idp-B", self.audience, self.nonce, replay, self.now),
        ]
        with self.assertRaises(ValueError):
            resolve_binding(validated, self.registry)

    def test_assertion_replay_is_rejected(self):
        replay = set()
        token, key = self.assertion("A", "demo-001", "same-jti")
        validate_assertion(token, key, "synthetic-idp-A", self.audience, self.nonce, replay, self.now)
        with self.assertRaises(ValueError):
            validate_assertion(token, key, "synthetic-idp-A", self.audience, self.nonce, replay, self.now)

    def request(self, layer="L2", operation="read"):
        return {
            "session_id": "sid-1",
            "subject_anchor": anchor_for_slot("demo-001"),
            "requester_id": "worker-demo-01",
            "requester_role": "social_worker",
            "purpose": "family_reunification",
            "case_id": "CASE-SYN-001",
            "layer": layer,
            "operation": operation,
        }

    def consent(self, level="L2"):
        return {
            "session_id": "sid-1",
            "subject_anchor": anchor_for_slot("demo-001"),
            "purpose": "family_reunification",
            "level": level,
            "expires_at": self.now + 300,
        }

    def test_l2_requires_consent(self):
        allowed, reason, _ = policy_decision(self.request("L2"), None, None, self.now)
        self.assertFalse(allowed)
        self.assertEqual(reason, "consent-required")

    def test_l3_requires_step_up_consent(self):
        allowed, reason, _ = policy_decision(self.request("L3"), self.consent("L2"), None, self.now)
        self.assertFalse(allowed)
        self.assertEqual(reason, "step-up-consent-required")

    def test_l4_requires_independent_legal_order(self):
        allowed, reason, _ = policy_decision(self.request("L4"), self.consent("L3"), None, self.now)
        self.assertFalse(allowed)
        self.assertEqual(reason, "independent-legal-authorization-required")

    def test_l4_scoped_order_allows_read(self):
        order = {
            "type": "judicial_order",
            "case_id": "CASE-SYN-001",
            "purpose": "family_reunification",
            "requester": "worker-demo-01",
            "operations": ["read"],
            "exp": self.now + 60,
        }
        allowed, reason, fields = policy_decision(self.request("L4"), self.consent("L3"), order, self.now)
        self.assertTrue(allowed)
        self.assertEqual(reason, "allow")
        self.assertIn("sealed_note", fields)

    def test_bulk_export_is_denied(self):
        allowed, reason, _ = policy_decision(self.request("L3", "bulk_export"), self.consent("L3"), None, self.now)
        self.assertFalse(allowed)
        self.assertEqual(reason, "bulk-export-denied")

    def test_ai_l4_is_denied(self):
        allowed, reason, _ = policy_decision(self.request("L4", "ai_context"), self.consent("L3"), None, self.now)
        self.assertFalse(allowed)
        self.assertEqual(reason, "ai-l4-denied")

    def test_ai_context_rejects_identity_fields(self):
        with self.assertRaises(ValueError):
            minimize_ai_context({"case_alias": "x", "national_id": "synthetic-but-forbidden"})

    def test_audit_chain_changes_when_event_changes(self):
        event = {"seq": 1, "action": "read", "subject_ref": "aud-x"}
        digest = audit_hash("GENESIS", event)
        tampered = dict(event)
        tampered["action"] = "export"
        self.assertNotEqual(digest, audit_hash("GENESIS", tampered))


if __name__ == "__main__":
    unittest.main()
