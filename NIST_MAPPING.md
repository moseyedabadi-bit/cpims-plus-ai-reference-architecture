# NIST Alignment Mapping

## Important statement

This document is an architectural cross-reference. It is **not** a certification, authorization, conformity assessment, or claim that the implementation satisfies every control objective.

Formal compliance would require scoping, impact categorization, control tailoring, implementation evidence, assessment procedures, and independent review.

## Reference mapping

| Architecture concern | Primary NIST reference | Project interpretation |
|---|---|---|
| Identity proofing | SP 800-63A-4 | proof identity at an assurance appropriate to risk |
| Authentication | SP 800-63B-4 | cryptographic authenticators; local biometric activation where used |
| Federation | SP 800-63C-4 | signed assertions, audience restriction, freshness, replay protection |
| Pairwise pseudonyms | SP 800-63C-4 | different domain/RP identifiers to reduce linkability |
| Derived attributes | SP 800-63C-4 | expose the minimum result rather than unnecessary raw attributes |
| Zero Trust | SP 800-207 | no implicit trust based on network location or ownership |
| Cloud-native/workload ZT | SP 800-207A | workload identity and granular application/service policy |
| Access enforcement | SP 800-53 AC family | enforce decisions at protected resources |
| Information flow | SP 800-53 AC family | constrain cross-domain flow and correlation |
| Separation of duties | SP 800-53 AC-5 | separate identity, infrastructure, DB, audit, privacy and AI administration |
| Least privilege | SP 800-53 AC-6 | minimum rights for humans and workloads |
| Audit/accountability | SP 800-53 AU family | attributable, protected audit evidence |
| Identification/authentication | SP 800-53 IA family | administrative and service identity assurance |
| Cryptographic protection | SP 800-53 SC family | separated keys and protected transport/storage |
| Contingency/backup | SP 800-53 CP family | domain-preserving recovery |
| Incident response | SP 800-53 IR family | detect, contain, revoke, investigate |
| System integrity | SP 800-53 SI family | vulnerability, integrity and monitoring controls |
| Supply chain | SP 800-53 SR family | model/image/library/provider dependency risk |
| Privacy controls | SP 800-53 PT family + Privacy Framework | data processing, minimization, transparency and risk |
| Organizational cyber governance | CSF 2.0 | govern, identify, protect, detect, respond, recover |
| AI governance | AI RMF GOVERN | roles, policy, accountability and culture |
| AI context/risk | AI RMF MAP | intended use, affected people and impact |
| AI testing | AI RMF MEASURE | validity, safety, bias, privacy and reliability evaluation |
| AI risk treatment | AI RMF MANAGE | prioritize and manage measured risks |

## Project-specific enhancements

These are not presented as NIST requirements:

- three independent identity providers;
- 2-of-3 valid assertion rule;
- independent/judicial authorization for L4 disclosures;
- layered consent manifest and step-up model;
- explicit prohibition on a global child identifier;
- `AICTX` ephemeral model context identifier;
- no global superadmin architectural invariant;
- synthetic-only release gates before real data.

## Zero Trust policy model

The project maps authorization conceptually as:

```text
Subject + Auth Assurance + Device/Workload
             +
Resource + Data Classification
             +
Purpose + Case Assignment + Consent/Authority
             +
Risk + Time
             ↓
Policy Decision
             ↓
Policy Enforcement
```

Network location alone is never sufficient.

## AI RMF cycle

### GOVERN
Define the charter, prohibited uses, roles, accountability, escalation, review, provider obligations, and lifecycle governance.

### MAP
Document intended use, affected children/families/beneficiaries, institutional context, foreseeable misuse, dependency assumptions, and downstream effects.

### MEASURE
Test hallucination, calibration, subgroup performance, privacy leakage, prompt injection, data exfiltration, overreliance, re-identification, and human factors.

### MANAGE
Limit or disable unsafe capabilities, change models/policies, reduce data, add oversight, document residual risk, and stop deployment when risk cannot be reduced sufficiently.

## Implementation evidence expected in a future assessment

A real assessment would need evidence such as:

- architecture and data-flow diagrams;
- inventory of systems/workloads/data;
- control implementation statements;
- provider contracts and assurance evidence;
- identity/authentication configuration;
- key-management procedures;
- policy-engine rules and tests;
- access and audit logs;
- incident and recovery exercises;
- synthetic red-team results;
- AI evaluation results;
- privacy risk assessment;
- governance and appeal procedures.

## Language discipline

Preferred wording:

> "Designed to align with selected NIST principles and publications."

Avoid without an actual assessment:

> "NIST certified"

> "NIST compliant"
