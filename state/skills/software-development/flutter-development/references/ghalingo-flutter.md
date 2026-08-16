# GhaLingo Flutter Project Notes

Living project-state reference for the GhaLingo **Flutter** rebuild. Update this file when
contract decisions, fixed defects, or conventions change. (The Kotlin original lives in the
`kotlin-mobile-development` skill's `references/ghalingo.md`.)

## Repo Facts

- Repo: `C:\Users\bohen\Documents\Hermes\ghalingo_flutter` (NOT yet a git repo — `flutter
  create` skips `git init`; init + commit when milestone 1 is accepted).
- Package: `com.ghanaspeech` (org flag); platforms: android, ios, web.
- Re-implements the Kotlin collector (`com.ghanaspeech.collector`) against the same Express
  backend (`ghana-speech-admin`) and the same frozen `openapi.yaml`.
- Resolved deps (2026-08): Flutter 3.35.7 / Dart 3.9.2, flutter_riverpod 2.6.1,
  go_router 14.8.1, dio 5.11.0, record 5.2.1, path_provider 2.1.5, device_preview 1.3.1.
- `flutter` + `dart` on PATH (no JAVA_HOME needed for web-only work).

## Contract Facts (mirrored from the Kotlin side)

- baseUrl is host-only (`http://localhost:3000/` default, `--dart-define=API_BASE_URL` to
  override). Endpoint paths carry the full `api/v1/...` prefix — do NOT add it to baseUrl.
- Canonical wire naming is snake_case; Flutter models map via manual `fromJson` reading
  snake_case keys (Kotlin properties stay camelCase).
- Chunk upload: raw audio bytes as body (`application/octet-stream`), `upload_id` +
  `chunk_index` (1-based) as QUERY params. No `md5_checksum` field exists.
- Backend quirk: `ValidationResult.isValid` is **camelCase** on the wire while everything
  else is snake_case — mirrored verbatim in `upload.dart`.
- Auth is mocked server-side (`mock-jwt-token-for-<id>`); backend auth hardening is still
  on the shared milestone list.

## Milestone Status

- **M1 DONE (2026-08):** scaffold + layered architecture; auth/missions/prompts/record
  vertical slice; fake repository (USE_FAKE_API default true); web recording via `record`
  (dev-preview webm); device_preview phone frame in Chrome. Verified: analyze clean,
  6/6 tests (4 contract models + 2 auth controller), `flutter build web` green, app live.
- **M2 NEXT:** offline-first queue (persist pending recordings + metadata) + chunked
  start→chunk→complete upload pipeline with resume + retry cap.
- **M3:** real backend auth (argon2/bcrypt + JWT), token in flutter_secure_storage,
  auth redirect in go_router.

## Run / Verify

```bash
cd /c/Users/bohen/Documents/Hermes/ghalingo_flutter
flutter run -d chrome --web-port=8080                      # browser preview (fake repo)
flutter run -d chrome --web-port=8080 --dart-define=USE_FAKE_API=false  # real backend on :3000
flutter analyze && flutter test                            # canonical checks
```

## Test Inventory

- `test/contract_models_test.dart` — pins snake_case wire shapes (Mission, Prompt,
  AuthResponse nested user, ValidationResult camelCase quirk).
- `test/auth_controller_test.dart` — pins login→TokenStore→auth-state wiring and logout,
  via `ProviderContainer` + `speechRepositoryProvider.overrideWithValue(FakeSpeechRepository())`.

## Known Open Defects (Flutter side)

- Web recording produces webm/opus (browser MediaRecorder), not 16 kHz PCM WAV — research
  capture is mobile-only. Documented in `audio_recorder_service.dart`.
- Upload "save" button on the record screen is a placeholder snackbar — real pipeline is M2.
- Auth redirect not wired into go_router (deferred to M3 with secure storage).
