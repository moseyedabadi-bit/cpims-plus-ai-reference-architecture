# Security reference implementation

This directory contains a **synthetic-only, dependency-free reference implementation** of the security properties defined in the architecture documents. It is intentionally small enough to inspect and test.

Implemented properties include 2-of-3 independent identity attestations, issuer/audience/nonce/freshness/replay checks, private subject binding, domain-scoped pairwise pseudonyms, purpose-bound consent, step-up consent for L3, separate legal/emergency grants for L4, denial of L4 export, AI identity minimization, and tamper-evident audit chaining.

Run:

```bash
cd implementation/security
python -m unittest -v test_reference.py
```

The current suite contains 11 tests. Passing these tests demonstrates only that this **reference code** enforces the modeled properties; it does not certify a deployed CPIMS+/Primero environment.

## Production substitutions

The PoC assertion MAC is deliberately simple and must not be treated as a production federation protocol. A production implementation should use vetted standards/libraries, phishing-resistant authenticators appropriate to the assurance target, managed key material, independent provider administration, resilient replay storage, privileged-access controls, independently administered audit, and formal legal/privacy/child-protection review.

The policy engine intentionally treats consent and legal authority as distinct grant types. Infrastructure administrators are not represented as case-data decision roles, and a judicial actor is modeled as an authorization issuer rather than a permanent database superuser.
