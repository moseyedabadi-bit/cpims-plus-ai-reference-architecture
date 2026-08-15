# Threat Model

## Scope

This threat model covers identity, consent, access control, data domains, AI, audit, providers, administrators, and institutional misuse. It treats both unauthorized attackers and misuse of legitimate authority as relevant risks.

## Protected assets

- real-world identity;
- family and social graph;
- case history;
- health and psychological information;
- consent state;
- AI recommendations;
- human decisions;
- authorization records;
- audit integrity;
- cryptographic keys;
- metadata that can enable re-identification.

## Threat actors

- external attacker;
- malicious or compromised social worker;
- compromised administrator;
- malicious insider;
- compromised identity provider;
- compromised AI/model provider;
- colluding administrators;
- supply-chain attacker;
- actor using lawful or institutional authority beyond the original humanitarian purpose;
- future actor attempting cross-dataset correlation.

## Architectural security properties

1. One identity-provider compromise cannot establish a valid normal session.
2. A stolen identifier is not sufficient for authorization.
3. A breach of one data domain does not reveal the complete person.
4. AI cannot directly query protected data stores.
5. No single administrator can independently join all identity and case domains.
6. Sensitive access is purpose-bound, time-bound, and auditable.
7. Consent revocation invalidates dependent access.
8. L4 access is scoped and independently authorized; no bulk judicial browse role exists.
9. AI can abstain and cannot autonomously execute high-impact decisions.
10. Backups preserve compartmentalization.

## Core abuse cases and expected controls

| Scenario | Primary control | Expected result |
|---|---|---|
| One IdP compromised | 2-of-3 independent assertion policy | No valid normal session |
| Session token stolen | short TTL, binding, replay protection, PEP | Limited/rejected use |
| Case identifier leaked | identifier is not authority | No access |
| Family DB stolen | domain PPI + separated keys | No direct real identity |
| Two domains correlated | scoped PPIs + controlled correlation service | Reduced linkage |
| Administrator compromised | separation of duties + key separation | No whole-person reconstruction |
| Social worker browsing unrelated cases | case assignment + purpose + consent + audit | Deny/alert |
| L3 requested without step-up | consent policy | Deny |
| L4 requested without independent authorization | independent authorization | Deny |
| Bulk export requested | default deny + no bulk capability | Deny |
| AI prompt injection | AI has no authorization power; context gateway | No policy bypass |
| AI hallucination | evidence/uncertainty + human-in-command | Human review required |
| AI overconfidence | calibrated confidence + abstention | Uncertainty exposed |
| Model bias | subgroup evaluation + appeal + monitoring | Detect/manage risk |
| Vector DB leaks | treat embeddings as protected data | Contain/rotate/delete |
| Backup stolen | domain-separated encryption and keys | Limited disclosure |
| Consent revoked mid-session | revocation propagation | dependent access terminated |
| Break-glass abuse | short TTL + reason + alert + independent review | detectable misuse |
| IdP outage | remaining 2 of 3 | service continuity |
| Two IdPs unavailable | emergency safeguarding process only | no normal authentication |
| Provider collusion | provider independence + gateway scope | residual risk remains |
| Institutional/legal mass demand | no central global export, scoped access, audit | reduced scale; not impossible |

## Highest residual risks

### Institutional control of the full deployment

If one institution ultimately controls source code, deployment, policy engine, keys, administrators, and legal authority, technology cannot guarantee resistance to a deliberate redesign of the system. Governance, independent oversight, transparency, and legal safeguards remain necessary.

### Correlation and re-identification

Pseudonymization is not anonymization. Age, region, family structure, dates, rare events, access metadata, and social relationships can permit re-identification.

### Consent under power imbalance

A beneficiary may technically approve disclosure while feeling that refusal would reduce access to help. The user experience and organizational policy must preserve meaningful choice wherever compatible with safeguarding obligations.

### Multi-party collusion

Distributed trust increases the number of actors required for abuse but does not eliminate the possibility of coordinated abuse.

## Mandatory red-team tests before real data

- compromise each IdP individually;
- compromise each data domain individually;
- compromise policy admin, DB admin, infrastructure admin, and AI admin independently;
- attempt cross-domain linkage;
- attempt token replay;
- attempt consent bypass;
- attempt L4 access without authorization;
- attempt bulk export;
- attempt prompt injection through case notes/documents;
- attempt model data exfiltration;
- test backup restoration without collapsing trust domains;
- test provider outages;
- test revocation propagation;
- test emergency/break-glass abuse;
- test audit tampering;
- test human automation bias through controlled studies.

## Acceptance rule

> If any single normal component compromise reveals the complete identity, life history, and sensitive case context of a beneficiary, the architecture fails its primary security objective.
