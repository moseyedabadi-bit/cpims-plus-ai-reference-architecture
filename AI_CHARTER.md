# AI Charter

## Purpose

The AI layer exists to assist accountable professionals. It is not an autonomous authority over children, families, refugees, beneficiaries, or service eligibility.

## Allowed uses

AI may:

- summarize approved case context;
- retrieve and organize evidence;
- compare permitted records;
- identify inconsistencies or missing evidence;
- generate alternative hypotheses for human review;
- explain factors behind a recommendation;
- estimate uncertainty;
- abstain when evidence is insufficient.

## Prohibited autonomous actions

AI must not independently:

- approve or reject family reunification;
- remove a child from a family;
- deny essential services;
- determine legal status;
- authorize sensitive disclosure;
- initiate punitive, military, police, immigration, or judicial action;
- create political, ethnic, religious, security, or behavioral target profiles;
- train on production beneficiary data by default;
- bypass the Policy Enforcement Point;
- request or discover real identity when identity is not required for the approved purpose.

## Required output contract

High-impact AI output should contain, where applicable:

```yaml
evidence: []
recommendation: null
confidence: null
uncertainty: null
missing_evidence: []
alternative_explanations: []
model_version: null
```

Valid outputs include:

- `INSUFFICIENT_EVIDENCE`
- `HUMAN_INVESTIGATION_REQUIRED`

## Human-in-command

An accountable human must be able to:

- reject the model's recommendation;
- correct incorrect source data;
- request additional evidence;
- record disagreement with the model;
- initiate appeal/review processes.

Organizational performance metrics must not penalize a professional merely for disagreeing with AI.

## Model access

AI has no direct database credentials. It receives a minimized context envelope only after authorization by the policy system.

AI context identifiers are ephemeral and purpose-specific. They are not persistent person identifiers.

## Bias and safety

Before use in a high-impact workflow, the model must be evaluated for:

- subgroup performance;
- foreseeable disparate impact;
- hallucination/error modes;
- overconfidence;
- prompt injection and untrusted-content attacks;
- data leakage;
- inappropriate inference from proxy variables;
- human automation bias.

## Training policy

Production beneficiary data is not a default training corpus. Any proposed training use requires a separate governance process, data minimization, de-identification/re-identification risk assessment, documented purpose, and independent approval.

## Audit

Each material AI-assisted action must be attributable to a model/version, policy version, input data classes, output, and final human action without storing unnecessary raw identity data in the AI audit record.
