from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import tempfile
import unittest

from reference import (
    AIContextBuilder,
    AccessRequest,
    AuditChain,
    AuthorizationGrant,
    ConsentReceipt,
    PolicyEngine,
    Provider,
    SecurityError,
    SubjectBindingRegistry,
    TrustGateway,
    derive_pairwise_id,
    sign_assertion,
)

UTC = timezone.utc


class SecurityReferenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 15, 10, 0, tzinfo=UTC)
        self.providers = [
            Provider("idp-a", b"a" * 32),
            Provider("idp-b", b"b" * 32),
            Provider("idp-c", b"c" * 32),
        ]
        self.subjects = {"idp-a": "pa_91", "idp-b": "pb_27", "idp-c": "pc_44"}
        registry = SubjectBindingRegistry({(issuer, subject): "anchor-synthetic-001" for issuer, subject in self.subjects.items()})
        self.gateway = TrustGateway(self.providers, registry)
        self.nonce = "challenge-123"

    def assertion(self, issuer, jti=None, audience="cpims-plus", subject=None):
        provider = next(p for p in self.providers if p.issuer == issuer)
        payload = {
            "iss": issuer,
            "aud": audience,
            "iat": self.now.isoformat().replace("+00:00", "Z"),
            "exp": (self.now + timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
            "auth_time": self.now.isoformat().replace("+00:00", "Z"),
            "jti": jti or f"{issuer}-jti",
            "sub": subject or self.subjects[issuer],
            "nonce": self.nonce,
        }
        return sign_assertion(payload, provider.secret)

    def test_two_of_three_establishes_session(self):
        token, session = self.gateway.establish_session(
            [self.assertion("idp-a"), self.assertion("idp-b")], self.nonce, self.now
        )
        self.assertEqual(session.subject_anchor, "anchor-synthetic-001")
        self.assertEqual(self.gateway.verify_session(token, self.now).assurance, "project-2-of-3")

    def test_one_provider_is_denied(self):
        with self.assertRaises(SecurityError):
            self.gateway.establish_session([self.assertion("idp-a")], self.nonce, self.now)

    def test_wrong_audience_is_denied(self):
        with self.assertRaises(SecurityError):
            self.gateway.establish_session(
                [self.assertion("idp-a", audience="other"), self.assertion("idp-b")], self.nonce, self.now
            )

    def test_replay_is_denied(self):
        a = self.assertion("idp-a", "replay-a")
        b = self.assertion("idp-b", "replay-b")
        self.gateway.establish_session([a, b], self.nonce, self.now)
        with self.assertRaises(SecurityError):
            self.gateway.establish_session([a, self.assertion("idp-c", "fresh-c")], self.nonce, self.now)

    def test_cross_subject_binding_is_denied(self):
        registry = SubjectBindingRegistry(
            {
                ("idp-a", self.subjects["idp-a"]): "anchor-one",
                ("idp-b", self.subjects["idp-b"]): "anchor-two",
            }
        )
        gateway = TrustGateway(self.providers, registry)
        with self.assertRaises(SecurityError):
            gateway.establish_session([self.assertion("idp-a"), self.assertion("idp-b")], self.nonce, self.now)

    def test_ppi_differs_by_domain(self):
        family = derive_pairwise_id("anchor-synthetic-001", "family", b"f" * 32)
        social = derive_pairwise_id("anchor-synthetic-001", "social", b"s" * 32)
        self.assertNotEqual(family, social)

    def test_l3_requires_step_up_consent(self):
        policy = PolicyEngine()
        request = AccessRequest("social_worker", "worker-1", "anchor", True, "family_reunification", 3)
        consent = ConsentReceipt("c1", "anchor", "worker-1", "family_reunification", 3, self.now, self.now + timedelta(hours=1), False)
        self.assertFalse(policy.evaluate(request, consent=consent, now=self.now).allowed)
        consent.step_up = True
        self.assertTrue(policy.evaluate(request, consent=consent, now=self.now).allowed)

    def test_l4_consent_alone_is_not_enough(self):
        policy = PolicyEngine()
        request = AccessRequest("social_worker", "worker-1", "anchor", True, "family_reunification", 4)
        consent = ConsentReceipt("c1", "anchor", "worker-1", "family_reunification", 4, self.now, self.now + timedelta(hours=1), True)
        self.assertFalse(policy.evaluate(request, consent=consent, now=self.now).allowed)
        grant = AuthorizationGrant(
            "j1", "judicial_order", "anchor", "worker-1", "family_reunification", frozenset({4}), frozenset({"read"}),
            "judicial-authority-opaque", self.now, self.now + timedelta(minutes=45), "case_specific_order", "L4-review"
        )
        self.assertTrue(policy.evaluate(request, consent=consent, grant=grant, now=self.now).allowed)

    def test_l4_export_has_no_path(self):
        policy = PolicyEngine()
        request = AccessRequest("social_worker", "worker-1", "anchor", True, "family_reunification", 4, "export")
        grant = AuthorizationGrant(
            "j1", "judicial_order", "anchor", "worker-1", "family_reunification", frozenset({4}), frozenset({"read"}),
            "judicial-authority-opaque", self.now, self.now + timedelta(minutes=45), "case_specific_order", "L4-review"
        )
        self.assertFalse(policy.evaluate(request, grant=grant, now=self.now).allowed)

    def test_ai_context_rejects_identity(self):
        builder = AIContextBuilder()
        with self.assertRaises(SecurityError):
            builder.build({"name": "نمونه", "age": 11}, "family_reunification")
        context = builder.build(
            {"age": 11, "case_status": "open", "coarse_region": "region-3", "family_relation": "candidate", "evidence": ["synthetic-e1"]},
            "family_reunification",
        )
        self.assertEqual(context["age_group"], "10-12")
        self.assertNotIn("age", context)
        self.assertTrue(context["ai_ctx"].startswith("aictx_"))

    def test_audit_chain_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            chain = AuditChain(path, b"k" * 32)
            chain.append({"actor": "worker-pseudonym", "case": "ppi_case_x", "action": "read", "purpose": "family_reunification"})
            chain.append({"actor": "worker-pseudonym", "case": "ppi_case_x", "action": "ai_context", "purpose": "family_reunification"})
            self.assertTrue(chain.verify())
            lines = path.read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[0])
            record["event"]["action"] = "tampered"
            lines[0] = json.dumps(record, ensure_ascii=False, sort_keys=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.assertFalse(chain.verify())


if __name__ == "__main__":
    unittest.main()
