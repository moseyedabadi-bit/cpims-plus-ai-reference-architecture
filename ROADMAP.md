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

## Phase 1 — Persian Primero overlay and synthetic reference implementation

- [x] Pin Primero upstream to v2.14.5.
- [x] Add reproducible `fa-IR` locale generator based on the complete upstream `fa-AF` key structure.
- [x] Add RTL, locale-registration and fallback patcher for Primero.
- [x] Add locale QA for missing keys and Iranian-Persian terminology review candidates.
- [x] Add GitHub Actions validation against the pinned Primero release.
- [ ] Complete professional Iranian Persian review by child-protection/legal/medical specialists.
- [ ] Obtain and review an authorized official CPIMS+ configuration bundle for deployment-specific localization.
- [ ] Build synthetic beneficiary/family/case generator.
- [ ] Implement local hardware-backed authenticator proof simulation.
- [x] Implement three independent test IdPs in the security reference.
- [x] Implement 2-of-3 assertion validation at Trust Gateway.
- [x] Implement subject binding registry with no case narratives.
- [x] Implement scoped session credentials.
- [x] Implement purpose-bound consent and step-up authorization model.
- [x] Implement Policy Decision reference for L1-L4.
- [x] Implement domain PPIs.
- [x] Implement AI Context Builder with raw identity rejection.
- [x] Implement tamper-evident audit PoC.
- [x] Implement L4 separation between consent and judicial/statutory/emergency grants.
- [x] Deny L4 bulk/export operations in the reference policy.

## Phase 2 — AI safety evaluation

- [ ] No-direct-database-access verification in an integrated Primero deployment.
- [ ] Prompt-injection tests using synthetic case documents.
- [ ] Hallucination and evidence-grounding evaluation.
- [ ] Confidence calibration and abstention testing.
- [ ] Subgroup/fairness evaluation on synthetic scenarios.
- [ ] Automation-bias study with simulated social-worker workflows.
- [ ] RAG/vector deletion and leakage tests.

## Phase 3 — Security and privacy red team

- [x] Unit-test compromise-equivalent condition where one IdP alone cannot establish a session.
- [ ] Compromise one deployed IdP.
- [ ] Compromise one deployed data domain.
- [ ] Compromise each administrative role independently.
- [ ] Attempt cross-domain re-identification.
- [x] Test assertion replay rejection in reference code.
- [x] Test audience/nonce/subject-binding failures in reference code.
- [x] Test consent/step-up bypass rejection in reference code.
- [x] Test L4 authorization bypass and export rejection in reference code.
- [x] Test audit tamper detection in reference code.
- [ ] Test break-glass abuse in an integrated environment.
- [ ] Test provider outage and recovery.
- [ ] Test backup/restore without collapsing trust domains.

## Phase 4 — Independent review

- [ ] Child-protection professional review.
- [ ] Iranian Persian terminology review.
- [ ] Privacy engineering review.
- [ ] Cybersecurity review.
- [ ] AI safety/governance review.
- [ ] Legal review for deployment jurisdiction.
- [ ] Human-rights/ethics review.
- [ ] Document unresolved residual risks.

## Real-data gate

Real beneficiary data remains out of scope unless all preceding gates are passed and an independent governance process explicitly approves a narrowly defined deployment.

A failed gate means: **NO REAL DATA**.
