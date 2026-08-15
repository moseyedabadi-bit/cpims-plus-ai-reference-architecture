# Data Governance

## Governing idea

Collect less, disclose less, retain less, and make every material disclosure explainable.

## Data classes

### L1 — Operational
Minimum workflow information required for routine service delivery.

### L2 — Sensitive social/family
Family relationships, social history, living situation, and professional case observations.

### L3 — Highly sensitive
Health, violence, abuse, psychological information, and other data whose disclosure can create serious harm.

### L4 — Exceptional/restricted
Information whose disclosure could enable targeting, coercion, severe discrimination, irreversible harm, or unsafe institutional repurposing.

## Data handling rule

Every request must answer:

- who is requesting;
- what exact fields are required;
- why they are required;
- which case/workflow authorizes the request;
- what consent or independent authority applies;
- how long access is needed;
- whether export is permitted;
- how the access will be audited.

## Minimum necessary

The Policy Enforcement Point should release only approved fields. Derived attributes are preferred over raw values when they answer the approved question.

Examples:

```text
Prefer: age_group = 10-12
Avoid : full_date_of_birth

Prefer: distance_band = near
Avoid : exact_home_address
```

## Domain separation

Identity, family, social, health, education, authorization, and audit domains use separate identifiers and cryptographic keys where feasible.

No single data store is intended to contain enough information to reconstruct the complete person.

## Pseudonymization

Pairwise/domain-scoped identifiers reduce linkage. They do not make data anonymous. Re-identification risk must be reassessed when fields, external datasets, AI capabilities, or threat actors change.

## Metadata

Metadata is treated as data. Logs, timestamps, IP/device details, query patterns, geographic hints, case-access sequences, and provider transaction IDs can enable correlation.

Metadata collection must therefore be purpose-limited and retained only as long as required.

## AI and RAG

Embeddings, vector indexes, prompts, responses, caches, chat history, and model traces are protected data when they are derived from protected information.

They must have explicit:

- scope;
- retention;
- encryption;
- deletion behavior;
- access policy;
- audit policy.

## Training

Production beneficiary data is excluded from model training by default. A training exception requires an independent governance workflow and documented re-identification risk assessment.

## Lifecycle

```text
Collect → Classify → Pseudonymize → Store → Use → Disclose → Expire → Delete → Backup expiry
```

Deletion design must account for replicas, caches, backups, vector stores, and downstream processors.

## Backup

Backups must preserve domain separation. A backup must not quietly create a more powerful central dataset than production.

## Export

Bulk export is denied by default. Exceptional export must be explicitly authorized, minimized, time-bound, attributable, and independently auditable.

## Data subject/beneficiary rights model

Where compatible with safeguarding and applicable law, the architecture should support:

- transparency about what is held;
- correction of inaccurate information;
- visibility into sensitive disclosures;
- revocation of optional consent;
- human review of AI-assisted outcomes;
- an appeal/review route.

## Synthetic data policy

Public development and demonstration use synthetic identities, families, cases, events, and tokens only.
