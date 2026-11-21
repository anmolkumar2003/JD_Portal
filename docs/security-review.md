# Security review (OWASP Top 10) — Phase 7

Date: 2026-11-21 · Scope: HR Recruitment Portal (local Docker stack)

## Summary

Mitigations already in place or added for the local/pilot build. Scores remain advisory and never auto-reject.

| OWASP | Status | Notes |
| --- | --- | --- |
| A01 Broken Access Control | Mitigated | JWT + `require_roles` + record-level job access (`AUTH-02/06`) |
| A02 Cryptographic Failures | Mitigated | argon2 passwords; secrets in env; signed MinIO URLs |
| A03 Injection | Mitigated | SQLAlchemy parameterized queries; Zod/Pydantic validation |
| A04 Insecure Design | Mitigated | Human-in-the-loop scoring; no sensitive features in matcher |
| A05 Security Misconfiguration | Partial | CORS allowlist; security headers middleware; HSTS for prod only |
| A06 Vulnerable Components | Partial | Pin deps; run `pip audit` / `npm audit` in CI before prod |
| A07 Auth Failures | Mitigated | Lockout after 5 failures; refresh cookie; short access TTL |
| A08 Software/Data Integrity | Partial | Alembic-only schema changes; checksum on uploads |
| A09 Logging Failures | Mitigated | Request IDs; no PII in application logs; append-only audit_logs |
| A10 SSRF | Low risk | No user-controlled server-side URL fetch in v1 |

## Upload hardening

- MIME + magic-byte validation (`cv_validation`)
- 5 MB size limit
- Stored in MinIO with opaque keys; downloads via short-lived signed URLs
- ClamAV scan status field reserved (optional worker in later hardening)

## Headers (API)

Recommended middleware values for production:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` on the Next.js app (careers + portal)
- `Strict-Transport-Security` only behind HTTPS

## Rate limits

- Public apply: 5 / IP / hour
- Authenticated API: 100 / user / minute (Redis)

## Findings to track

1. AUTH-04 TOTP not enabled by default (optional).
2. ClamAV not wired in the local compose file (document for prod).
3. Docker daemon must be running for full integration verification.

## Remediation owners

Engineering team before pilot go-live; legal confirmation for GDPR/DPDP retention windows.
