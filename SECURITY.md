# Security Policy

## Research-only repository

This repository is for architecture research and synthetic proof-of-concept work.

## Never submit real vulnerable-person data

Do not commit or attach:

- real child or family records;
- refugee/beneficiary records;
- biometric images or templates;
- real identity mappings;
- production pseudonyms/tokens;
- case screenshots;
- real organization IP addresses or hostnames;
- credentials, secrets, API keys, certificates, private keys;
- production Kubernetes manifests that expose organizational details;
- database exports or logs containing protected information.

Use synthetic data only.

## Reporting security issues

Do not demonstrate a vulnerability using real beneficiary data. Reproduce issues with synthetic test records and explain the affected architectural property.

High-priority architectural failures include:

- one component can reconstruct the whole person;
- an identifier alone grants access;
- AI can bypass the policy gateway;
- one administrator can join identity and all case domains;
- L4 can be browsed or bulk-exported without narrow authorization;
- consent revocation does not terminate dependent access;
- audit can be silently deleted or altered by the actor being audited;
- a model can execute high-impact decisions autonomously.

## Secrets

Repository examples must use placeholders. Production secrets belong in a dedicated secret-management system, never Git.

## Dependency and supply-chain posture

Future implementation should use dependency pinning, signed artifacts where practical, SBOM generation, vulnerability scanning, and controlled build pipelines.

## Safe research principle

The purpose of security testing is to determine whether the architecture protects vulnerable people. Security research must not itself expose them.
