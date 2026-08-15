# CPIMS+ / Primero Persian Implementation Overlay

This directory turns the repository's architecture into a **testable implementation overlay** for the open-source Primero platform used by CPIMS+.

## Scope and truth-in-labeling

- Upstream application: **Primero v2.14.5** (`primeroIMS/primero`).
- The public Primero source is open source, but the official CPIMS+ configuration bundles are distributed separately by the Primero/CPIMS+ maintainers.
- Therefore this repository does **not** claim to contain the official CPIMS+ configuration.
- The Persian work here is an **Iranian Persian (`fa-IR`) localization overlay** plus a security reference implementation based on this project's threat model.
- Real beneficiary data is prohibited in this repository and in the included tests.

## What is implemented

### Persian localization

`localization/` provides:

1. a reproducible generator that consumes the pinned upstream `fa-AF` translation and produces `fa-IR` with full upstream key coverage;
2. Iranian-Persian terminology normalization;
3. Gregorian date labels localized for Persian while keeping the application data model/calendar semantics unchanged;
4. a fail-closed patcher that adds `fa-IR` to Primero's supported and RTL locale lists and configures fallback `fa-IR -> fa-AF -> en`;
5. QA checks for missing keys and common Dari vocabulary that still needs normalization.

The generator pins upstream Git blob hashes so a changed upstream file is not silently accepted.

### Security reference

`security/` provides dependency-free, executable Python reference code and tests for:

- 2-of-3 independent identity-provider assertions;
- issuer, audience, nonce, freshness, TTL and replay validation;
- a private subject-binding registry;
- domain-scoped pairwise pseudonymous identifiers;
- purpose-, requester-, layer- and time-bound consent;
- separation between consent and judicial/statutory/emergency legal grants;
- L4 denial for bulk/export operations;
- short-lived AI context envelopes with identity-field rejection;
- tamper-evident, pseudonymous audit chaining.

This is **not production authentication code**. Production should use vetted federation/authentication protocols and libraries, hardware-backed authenticators where required, managed keys/HSM/KMS, independent audit infrastructure, and legal/child-protection/privacy review.

## Quick start

Clone the exact Primero release separately:

```bash
git clone --branch v2.14.5 --depth 1 https://github.com/primeroIMS/primero.git primero-v2.14.5
```

Generate `fa-IR`:

```bash
python implementation/localization/build_fa_ir.py --output ./build/fa-ir
```

Apply it to the separate Primero checkout:

```bash
python implementation/localization/apply_to_primero.py \
  --primero ./primero-v2.14.5 \
  --generated ./build/fa-ir
```

Then configure that Primero deployment to include `fa-IR` in its enabled locale list.

Run the security tests:

```bash
cd implementation/security
python -m unittest -v test_reference.py
```

Run localization unit tests:

```bash
cd implementation/localization
python -m unittest -v test_localization.py
```

## Persian UX decisions

- UI direction: RTL.
- Locale code: `fa-IR`.
- Internal timestamps and interoperability formats are **not converted to Jalali/Persian calendar by this overlay**. That is an intentional data-integrity/interoperability choice.
- The UI may later add Jalali *presentation* as a separately tested feature, but stored canonical dates should remain unambiguous and interoperable.
- Child-protection, legal, medical and safeguarding terminology requires human subject-matter review before real deployment.

## Production gate

Do not deploy with real child/family data until at minimum:

1. the Persian locale has professional linguistic and child-protection review;
2. the official/authorized CPIMS+ configuration is obtained through the appropriate channel;
3. the identity/federation design is implemented with production-grade protocols and independent providers;
4. the policy model is mapped to applicable law and safeguarding rules;
5. penetration testing, privacy review, AI evaluation and incident-response exercises are completed;
6. backups, audit, key management and privileged administration preserve the same trust separation as production.
