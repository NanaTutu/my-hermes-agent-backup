# GhaLingo Project Notes (Android side)

Living project-state reference for the GhaLingo Android app. Update this file whenever
the project state changes (contract decisions, fixed defects, new conventions).

## Repo Facts

- Repo: `C:\Users\bohen\Documents\Hermes\GhaLingo` (git, branch `master`, origin `https://github.com/NanaTutu/GhaLingo.git`)
- Two components: `android-project/` (this app) and `ghana-speech-admin/` (Express/TS backend + React admin)
- App package: `com.ghanaspeech.collector`
- Stack: Kotlin + Jetpack Compose + M3, Room, DataStore, Retrofit, WorkManager, Hilt, AudioRecord→WAV
- Build (bumped 2026-08-11, green assembleDebug): AGP 8.13.2, Kotlin 2.3.20, Hilt 2.57.2,
  Room 2.8.4, Gradle wrapper 9.0.0, compileSdk 35, targetSdk 34, minSdk 23
- **No JDK on PATH in the Hermes bash shell** — set `JAVA_HOME` (e.g. `/c/Program Files/Android/Android Studio/jbr`, JDK 21) before `./gradlew`, or Gradle exits 1 with "no java command found".
- Toolchain version rules (each verified by failure, then by green build):
  - Gradle 9.0.0 wrapper requires AGP 8.13+; AGP 9.x needs Gradle 9.1+.
  - Kotlin ≤ 2.2 does NOT run on Gradle 9. Kotlin 2.3.20 does.
  - Hilt 2.52 rejects Kotlin 2.3 stubs ("metadata version 2.3.0 > max 2.1.0"); 2.57.2 is the
    newest Hilt that supports Gradle 9.0.0 without demanding AGP 9 (2.59+ needs AGP 9).
  - Room 2.6.1 → 2.8.4 required for the same Kotlin-2.3 metadata reason.
- gradle.properties on this 7.7GB-RAM machine is memory-hardened: `-Xmx1536m`,
  `kotlin.compiler.execution.strategy=in-process`, `workers.max=1`, `parallel=false`.
  Default multi-JVM profile (forked Kotlin daemon + parallel kapt) crashes the Gradle
  daemon with native OOM (two verified `hs_err_pid*.log` crashes).
- `local.properties` points to `C:/Users/bohen/AppData/Local/Android/Sdk` (was a Linux path
  from another machine's clone — fixed 2026-08-11). SDK has platforms 34/35/36, build-tools 36.0.0, licenses accepted.
- No test files exist (TESTING.md describes a plan, not tests).

## Android ↔ Backend Contract Facts

- Contract source of truth: `openapi.yaml` at repo root (frozen 2026-08-11, mobile surface only).
  Canonical JSON naming is **snake_case**; Android maps via Gson `@SerializedName` (Kotlin
  properties stay camelCase). Admin endpoints are NOT in the contract yet.
- Retrofit `baseUrl` is `https://api.ghanaspeech.com/` (host only — fixed double-prefix bug);
  `SpeechApi.kt` paths carry the full `api/v1/...` prefix. Do NOT add `/api/v1/` to baseUrl.
- Chunk upload contract: raw audio bytes as body (application/octet-stream), `upload_id` +
  `chunk_index` as QUERY params, chunk_index 1-based (S3 PartNumber semantics). Server route
  mounts its own `express.raw({type: "application/octet-stream", limit: "6mb"})`.
- `uploads/start` accepts ONLY `{prompt_id, mission_id}` and returns
  `{upload_id, chunk_size_recommended_bytes}` — NO `expected_chunks` (client computes
  ceil(file_size / chunk_size)). Server recommends 5 MiB; Android falls back to 1 MiB if missing.
- `uploads/complete` body: `{upload_id, language, dialect, region, device_model, android_version}`.
  There is NO `md5_checksum` field — the Android MD5 computation was dropped (backend never validated).
- Auth responses: `{message, token, user}` — user is a nested snake_case object; Android
  `AuthResponse` reads `token` + `user.id`/`user.email` (no top-level userId).
- `GET /sync` query params: `last_sync` (ISO-8601) + `language`. Android passes both, not camelCase.
- Backend auth is mocked: login returns `mock-jwt-token-for-<id>`, `verifyToken` only checks header
  presence, admin routes largely open, user IDs hardcoded (2, 6). Treat backend auth as non-existent until fixed.
- Mobile endpoints: `/api/v1/auth/register|login`, `/api/v1/missions`, `/api/v1/missions/:id/prompts`,
  `/api/v1/uploads/start|chunk|complete`, `/api/v1/sync`, `/api/v1/health`.
- Smoke test: `ghana-speech-admin/scripts/contract-smoke-run.sh` exercises the full chain
  (register→login→missions→prompts→start→chunk×2 (real WAV bytes)→complete→sync) against a local server.
  Run from `ghana-speech-admin/` with `bash scripts/contract-smoke-run.sh`. Requires `npm run build` first.

## Known Android Defects (from Aug 2026 audit — reverify, don't assume)

1. **FIXED 2026-08-11**: BODY logging gated on `BuildConfig.DEBUG` (buildConfig=true added to app/build.gradle).
2. `AndroidManifest.xml` has `android:allowBackup="true"` with tokens/recordings/GPS on device → backup rules or `allowBackup="false"`.
3. `AudioServices.kt` suppresses `MissingPermission` before `startRecording()` → real runtime permission flow required.
4. Room `exportSchema = false`, no migrations → flip before release.
5. `stopRecording()` releases `AudioRecord` without joining the writer thread → WAV header corruption risk.
6. `SyncWorker.kt`: `cleanupLocalStorage()` is a stub; chunk resume not implemented (failed chunk restarts
   upload); upload session state lives only in RAM. **PARTIALLY FIXED 2026-08-11**: missing-file branch now
   deletes the zombie row instead of leaving it pending forever (`repository.deleteRecording`).
7. `MainActivity.kt` ~500 lines with hardcoded sample missions/prompts in `remember`; UI not wired to
   repository/ViewModels.
8. **RESOLVED 2026-08-11**: MD5 computation dropped from SyncWorker — contract has no checksum field.

## Recommended Order of Work (from codebase audit)

1. **DONE 2026-08-11**: API contract frozen (`openapi.yaml`, snake_case canonical), Retrofit
   baseUrl fixed, Android DTOs aligned with @SerializedName, chunk route raw-parser mounted,
   zombie-row fix, MD5 dropped. Verified end-to-end via `scripts/contract-smoke-run.sh`.
2. Real backend auth (argon2/bcrypt + JWT + role middleware, remove hardcoded IDs). ← NEXT
3. Split `server.ts` into routers/controllers.
4. Fix upload pipeline: persistent upload sessions, checksum/chunk validation, idempotent resume.
5. Wire Android UI to repository/ViewModels (kill hardcoded demo data).
6. Add tests: backend API tests; Android `TechnicalValidator`, Room DAO round-trips,
   repository tests with MockWebServer, WorkManager tests with `TestListenableWorkerBuilder`.
7. Fix `export.ts` archiver import warning (namespace import crashes at runtime) + dashboard chunk-splitting.
8. Real analytics + privacy controls (GPS consent, export anonymization, retention policy).

## Verification for GhaLingo Work

- After any contract change: grep `SpeechApi.kt` annotations vs `server.ts` route payloads — names and
  prefixes must match on both sides.
- After any sync change: checklist in main SKILL.md (zombie rows, persisted session, retry cap, cleanup age guard).
- After any build work: `./gradlew assembleDebug` must pass with JAVA_HOME set.
- Update this file when a defect is fixed so future sessions don't re-audit stale code.