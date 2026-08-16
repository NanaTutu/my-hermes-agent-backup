# GhaLingo Flutter Project Notes

Living project-state reference for the GhaLingo **Flutter** rebuild. Update this file
whenever project state changes (contract decisions, fixed defects, new conventions).

## Repo Facts

- Repo: `C:\Users\bohen\Documents\Hermes\ghalingo_flutter` (Flutter rebuild of the Kotlin client).
- Sibling project (same product, other client): `C:\Users\bohen\Documents\Hermes\GhaLingo`
  (see `kotlin-mobile-development` skill + its `references/ghalingo.md`).
- Package: `ghalingo_flutter`, org `com.ghanaspeech`, platforms android/ios/web.
- Backend: same `ghana-speech-admin/` Express server + frozen `openapi.yaml` contract (snake_case).
- Stack pins (pubspec): riverpod 2.6.1, go_router 14.8.1, dio 5.11.0, record 5.2.1,
  path_provider 2.1.5, device_preview 1.3.1, flutter_lints 5.0.0.
- Flutter 3.35.7 stable + Dart 3.9.2 on PATH (see SKILL.md for path).

## Config Switches (compile-time, `--dart-define`)

- `API_BASE_URL` — default `http://localhost:3000/` (host only, no path; endpoints carry
  the full `api/v1/...` prefix).
- `USE_FAKE_API` — default **true** (FakeSpeechRepository, bundled sample data). Flip to
  `false` when the real backend is wired (milestone 3). Flip the default in
  `core/config/app_config.dart` before release.

## What's Built (milestone 1 — done 2026-08-15)

- Layered architecture: core/config|network|router|theme, data/models|remote|repository,
  audio/, ui/controllers|screens|widgets.
- Screens: auth (login/register) → missions → prompts → record (mic + elapsed timer +
  level meter; upload button is a placeholder SnackBar).
- Data layer: `SpeechApi` (dio) + `SpeechRepository` interface + `SpeechRepositoryImpl` +
  `FakeSpeechRepository` + provider switch.
- Auth: `AuthController` (login/register/logout) → `TokenStore` → dio Bearer interceptor.
  Token is in-memory only (no secure storage yet).
- Audio: `AudioRecorderService` wraps `record`; WAV on mobile, webm/opus on web (dev-preview).
- Tests: 4 contract-model tests + 2 auth-controller tests (all green), `flutter analyze` clean,
  `flutter build web` green. Runs in Chrome at `localhost:8080` via device_preview phone frame.

## Contract Facts (from openapi.yaml — same as Kotlin client)

- snake_case canonical; Android/Dart map via explicit `fromJson`. ONE quirk:
  `ValidationResult.isValid` is **camelCase** on the wire (mirrored in `upload.dart`).
- `uploads/chunk`: raw octet-stream body, `upload_id` + `chunk_index` (1-based) query params.
- `uploads/start` returns `{upload_id, chunk_size_recommended_bytes}`; no `expected_chunks`.
- `uploads/complete` body `{upload_id, language, dialect, region, device_model, android_version}`
  — NO `md5_checksum`.
- Auth responses: `{message, token, user}` (user nested snake_case). Backend auth is mocked
  (`mock-jwt-token-for-<id>`, hardcoded ids 2/6) — treat as non-existent until milestone 3.

## Next Milestones

1. Offline-first local queue (pending → uploaded status) + chunked upload pipeline
   (start → chunk → complete) with persisted session state and retry cap.
2. Real backend auth (argon2/bcrypt + JWT + roles), swap `USE_FAKE_API` default to false.
3. Secure token storage (flutter_secure_storage) + auth redirect in go_router.
4. Upload-session persistence + idempotent resume; wire the record screen's Upload button.
5. More tests: dio endpoint contract tests, recorder controller, sync worker.

## Verification for GhaLingo Flutter Work

- After any contract change: grep `SpeechApi`/model `fromJson` field names against
  `openapi.yaml` — names and snake_case (or the `isValid` quirk) must match.
- After any build work: `flutter analyze` + `flutter test` + `flutter build web` must all pass.
- Update this file when a defect is fixed so future sessions don't re-audit stale code.
