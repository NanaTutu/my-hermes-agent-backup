# Comprehensive Codebase Report Example: GhaLingo Pattern

This reference captures reusable review patterns from a repository containing:

- Android Kotlin/Jetpack Compose field app;
- React/Vite admin dashboard;
- Express/TypeScript backend;
- PostgreSQL/MinIO/Redis abstractions with local fallbacks;
- offline speech-recording, sync, and dataset-export domain.

Use it as a checklist for similar full-stack/mobile codebase audits, not as a fact record about the current repo state.

## High-value inspection points

1. **Docs vs implementation**
   - README may claim production readiness or Clean Architecture.
   - Verify actual package layout, ViewModels, tests, auth, and infrastructure behavior.
   - Flag aspirational documentation separately from implemented behavior.

2. **Client/server contract drift**
   - Compare Android Retrofit DTOs, backend Express route bodies, admin fetch calls, and API docs.
   - Common blockers: camelCase vs snake_case, duplicated `/api/v1` in baseUrl plus endpoint annotations, response fields that do not match DTO names.

3. **Prototype security smell cluster**
   - Fake JWTs or tokens like `mock-jwt-token-*`.
   - Password hashes that are static placeholders.
   - Login that only checks user existence.
   - Admin routes without auth/role middleware.
   - Hardcoded user IDs in profile, upload, verification, or admin actions.
   - `Math.random()` used for verification/reset/upload IDs.

4. **Mobile privacy/security checks**
   - BODY-level HTTP logging in Android release paths.
   - `android:allowBackup="true"` while storing auth/user/recording/GPS data.
   - Suppressed missing permission warnings without explicit runtime permission flow.
   - GPS metadata collection without clear optionality/consent/export anonymization.

5. **Upload pipeline reality check**
   - Verify server can actually parse multipart/raw upload chunks.
   - Check whether sessions survive process restart.
   - Confirm checksum validation is performed, not only modeled.
   - Look for idempotency/resume semantics for bad networks.
   - Ensure chunk count, size limits, ownership, and cleanup are enforced.

6. **Fallback modes**
   - Local in-memory/local-disk fallbacks are useful for demos.
   - Make sure UI health/status text reflects actual fallback state instead of always claiming PostgreSQL/MinIO/Redis.
   - Separate demo convenience from production durability.

7. **Build/runtime verification**
   - Run typecheck/build/audit where possible.
   - Start the backend briefly and hit `/health` plus one core endpoint if safe.
   - Treat bundler warnings as findings when they indicate runtime crashes, e.g. namespace import called as a function.
   - Revert lockfile/generated changes caused by analysis unless user requested edits.

## Report language pattern

Use direct classification:

- "Strong proof-of-concept scaffold" when architecture direction is sound but implementation is mock-heavy.
- "Not production-ready" when auth, tests, persistence, API contracts, or upload durability are unresolved.
- "Do not add features yet; stabilize foundations" when surface area is already broad but core guarantees are weak.

## Recommended severity framing

- **P0**: real auth/authorization, API contract mismatch, upload durability/parsing/checksum, fake security-sensitive code, missing tests for critical paths.
- **P1**: oversized files, duplicated schema sources, hardcoded analytics, dashboard status mismatch, job/export reliability.
- **P2**: bundle splitting, config validation, observability, documentation wording, CI polish.
