# Roadmap

## Phase 0 — Architecture baseline

- [x] Define human-in-command principle.
- [x] Define distributed-trust identity concept.
- [x] Separate authentication from consent.
- [x] Define data classification L1-L4.
- [x] Define pairwise/domain-scoped pseudonymous identifiers.
- [x] Define ephemeral AI context model.
- [x] Define independent audit and no-global-superadmin principles.
- [x] Map architecture concepts to relevant NIST publications.

## Phase 1 — Synthetic reference implementation

- [ ] Build synthetic beneficiary/family/case generator.
- [ ] Implement local authenticator proof simulation.
- [ ] Implement three independent test IdPs.
- [ ] Implement 2-of-3 assertion validation at Trust Gateway.
- [ ] Implement subject binding registry with no case narratives.
- [ ] Implement scoped session credentials.
- [ ] Implement consent manifest and revocation.
- [ ] Implement Policy Decision/Enforcement Points.
- [ ] Implement domain PPIs and Correlation Service.
- [ ] Implement AI Context Builder and single-use AICTX.
- [ ] Implement append-only/tamper-evident audit PoC.

## Phase 2 — AI safety evaluation

- [ ] No-direct-database-access verification.
- [ ] Prompt-injection tests using synthetic case documents.
- [ ] Hallucination and evidence-grounding evaluation.
- [ ] Confidence calibration and abstention testing.
- [ ] Subgroup/fairness evaluation on synthetic scenarios.
- [ ] Automation-bias study with simulated social-worker workflows.
- [ ] RAG/vector deletion and leakage tests.

## Phase 3 — Security and privacy red team

- [ ] Compromise one IdP.
- [ ] Compromise one data domain.
- [ ] Compromise each administrative role independently.
- [ ] Attempt cross-domain re-identification.
- [ ] Attempt assertion/session replay.
- [ ] Attempt consent bypass.
- [ ] Attempt L4 authorization bypass.
- [ ] Attempt bulk export.
- [ ] Attempt audit tampering.
- [ ] Test break-glass abuse.
- [ ] Test provider outage and recovery.
- [ ] Test backup/restore without collapsing trust domains.

## Phase 4 — Independent review

- [ ] Child-protection professional review.
- [ ] Privacy engineering review.
- [ ] Cybersecurity review.
- [ ] AI safety/governance review.
- [ ] Legal review for deployment jurisdiction.
- [ ] Human-rights/ethics review.
- [ ] Document unresolved residual risks.

## Real-data gate

Real beneficiary data remains out of scope unless all preceding gates are passed and an independent governance process explicitly approves a narrowly defined deployment.

A failed gate means: **NO REAL DATA**.
