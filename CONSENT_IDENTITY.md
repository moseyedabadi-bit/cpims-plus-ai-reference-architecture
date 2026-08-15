# Consent and Identity Architecture

## Separation of concepts

Authentication answers: **Who is performing this action?**

Consent answers: **What is this person permitting for this purpose?**

They are deliberately separate.

## Local biometric use

Biometrics are intended only to unlock or activate a local trusted authenticator/private key. CPIMS+ does not store raw biometric samples or templates.

A non-biometric recovery/alternative path must exist for accessibility, failure, and exceptional cases.

## External identity providers

Three independent providers return signed authentication assertions. The Trust Gateway requires at least two valid assertions from the same authentication transaction.

The gateway validates at minimum:

- issuer;
- signature;
- intended audience;
- assertion freshness/expiry;
- nonce/request binding;
- replay state;
- required assurance level.

Providers do not issue persistent CPIMS+ case identifiers.

## Provider independence

Independence must be assessed across ownership, infrastructure, identity backend, keys, jurisdiction, DNS/CDN dependencies, SDKs, and operational administration.

Three brands backed by one critical identity backend do not provide three independent trust roots.

## Consent manifest

At the beginning of a workflow/session, the beneficiary should be shown an understandable manifest describing the requested purpose and data classes.

Example:

```yaml
purpose: family_reunification
requested:
  L1: required_for_workflow
  L2: optional_requested
  L3: not_requested
  L4: not_requested
expires: session_end
```

Moving into more sensitive layers requires step-up authorization/consent according to the policy for that data class.

## Consent receipt

A consent receipt should contain only the minimum necessary metadata:

```yaml
consent_id: opaque
subject: pseudonymous
purpose: family_reunification
scope: [L1, L2]
requester: scoped_worker_id
issued_at: timestamp
expires_at: timestamp
policy_version: version
revocable: true
```

## Coercion risk

A biometric confirmation is not evidence that consent was free, informed, or uncoerced. The service design must make clear which information is strictly necessary and which disclosure is optional.

Refusing optional disclosure should not silently become a denial of all basic assistance.

## Children and decision capacity

Age alone does not determine meaningful consent. The implementation must account for legal status, developmental capacity, safeguarding obligations, best-interest requirements, and local law.

These rules are governance requirements and must not be delegated to an AI model.

## L4 independent authorization

For L4 access, a separate authorization authority may be required. Where a judicial role is appropriate, the judge acts as a narrow authorization authority, not as a superuser.

The authorization must be case-specific, purpose-specific, operation-specific, and short-lived.

## Revocation

Revocation must propagate to dependent access grants and active sessions as quickly as technically and operationally feasible.

## Emergency access

Break-glass access is an exception path, not a substitute for consent. It requires a documented reason, minimal scope, short TTL, alerting, tamper-evident audit, and post-event independent review.
