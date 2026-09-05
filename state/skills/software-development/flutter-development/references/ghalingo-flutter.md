# GhaLingo Flutter Project Notes

Living project-state reference for the GhaLingo **Flutter** rebuild. Update this file when
contract decisions, fixed defects, or conventions change. (The Kotlin original lives in the
`kotlin-mobile-development` skill's `references/ghalingo.md`.)

## Repo Facts

- Repo: `C:\Users\bohen\Documents\Hermes\ghalingo_flutter` (NOT yet a git repo — `flutter
  create` skips `git init`; init + commit when the offline milestone is accepted).
- Package: `com.ghanaspeech` (org flag); platforms: android, ios, web.
- Re-implements the Kotlin collector (`com.ghanaspeech.collector`) against the same Express
  backend (`ghana-speech-admin`) and the same frozen `openapi.yaml`.
- Resolved deps (2026-08): Flutter 3.35.7 / Dart 3.9.2, flutter_riverpod 2.6.1,
  go_router 14.8.1, dio 5.11.0, record 5.2.1, path_provider 2.1.5, device_preview 1.3.1,
  sqflite 2.4.2, sqflite_common_ffi 2.3.7+1, sqflite_common_ffi_web 0.4.5+4, sqlite3 2.9.4,
  crypto 3.x, path 1.9.1, web 1.1.1.
- `flutter` + `dart` on PATH (no JAVA_HOME needed for web-only work).

## Offline Architecture (current)

The app is **fully offline** — the SQLite store is the real repository, not a fake.

- `lib/data/local/app_database.dart` — lazy singleton `AppDatabase`. Version-1 schema
  (users, session, missions, prompts, recordings) + first-run seed of 4 missions / 12
  prompts (moved out of the deleted `FakeSpeechRepository`).
  - Engine: `databaseFactory` (sqflite) on mobile; `databaseFactoryFfiWebNoWebWorker`
    on web (main-thread wasm, no shared-worker file needed).
  - Test seam: `AppDatabase.test(factory, {path})` injects a factory (ffi) + path.
- `lib/data/local/local_speech_repository.dart` — `LocalSpeechRepository implements
  SpeechRepository`: local auth (salted SHA-256 via `lib/core/security/password_hasher.dart`),
  persisted single-row session, missions/prompts read, recordings queue
  (audio stored as BLOB; list view joins prompt/mission text).
- `lib/data/repository/speech_repository.dart` — offline-first interface (register/login/
  currentUser/logout + getMissions/getMissionPrompts + saveRecording/getRecordings/
  deleteRecording). The old network upload methods (startUpload/uploadChunk/completeUpload)
  are GONE; they return as a sync layer in M2/M3.
- Dormant network scaffolding (kept for the future sync path): `lib/data/remote/speech_api.dart`,
  `lib/core/network/api_client.dart`, `lib/core/network/token_store.dart`, models
  `sync.dart` + `upload.dart`, `lib/core/config/app_config.dart` (`apiBaseUrl`,
  `uploadChunkSizeBytes`, `offlineMode`).
- `lib/audio/audio_io.dart` — conditional-import helper to read recorded bytes:
  `audio_io_io.dart` (File) vs `audio_io_web.dart` (`dart:js_interop` + `package:web` fetch
  of the blob URL) vs `audio_io_stub.dart`. `audio_io_web.dart` is why `web` is a direct dep.

### Web wasm setup (important)

- `web/sqlite3.wasm` is bundled at the web root (730 KB, version-matched to the `sqlite3`
  package). The no-web-worker factory loads it via relative URI `sqlite3.wasm`.
- Download a matching wasm from `https://github.com/simolus3/sqlite3.dart/releases/download/
  sqlite3-<version>/sqlite3.wasm` (match the resolved `sqlite3` package version) and drop it
  in `web/`. Re-download if the `sqlite3` version bumps.
- Do NOT run `dart run sqflite_common_ffi_web:setup` — it builds a shared worker (webdev
  toolchain) that isn't needed for the noWebWorker path.

## Milestone Status

- **M1 DONE (2026-08):** scaffold + layered architecture; auth/missions/prompts/record
  vertical slice; device_preview phone frame in Chrome. (Was fake-repo backed.)
- **M2 DONE — offline-first (2026-08):** SQLite persistence (sqflite + ffi_web), local auth
  with hashed passwords + persisted session/auto-login, seeded missions/prompts, recordings
  offline queue with a "My Recordings" screen (list + delete). Record screen "Save offline"
  writes audio bytes to the DB. Verified: analyze clean, 14/14 tests, `flutter build web`
  green, runtime web boot + wasm DB open confirmed (IndexedDB `sqflite_databases`).
- **M3 NEXT (sync + real auth):** chunked start→chunk→complete upload pipeline to the
  Express backend with resume + retry cap; backend auth (argon2/bcrypt + JWT) replacing the
  local hashed store; token in flutter_secure_storage; go_router auth redirect.

## Run / Verify

```bash
cd /c/Users/bohen/Documents/Hermes/ghalingo_flutter
flutter run -d chrome --web-port=8080                      # browser preview (offline SQLite)
flutter analyze && flutter test                            # canonical checks (14 tests)
flutter build web                                          # must succeed after dep/schema changes
```

## Test Inventory

- `test/contract_models_test.dart` — pins snake_case wire shapes (Mission, Prompt,
  AuthResponse nested user, ValidationResult camelCase quirk).
- `test/local_repository_test.dart` — the real SQLite repo against an in-memory ffi DB:
  seed, register/duplicate/login/verify/logout, recording round-trip.
- `test/auth_controller_test.dart` — AuthController wiring (login/error/logout/restoreSession)
  over the real repo.

### Test gotcha (sqflite path caching)

sqflite caches open `Database` handles **by path**, so a fixed `:memory:` is shared across
every test (causes "email already exists" cross-test leakage). Give each test a unique
shared-cache in-memory path:
`'file:ghalingo_test_<n>?mode=memory&cache=shared'`.

## Known Open Defects (Flutter side)

- Web recording produces webm/opus (browser MediaRecorder), not 16 kHz PCM WAV — research
  capture is mobile-only. Documented in `audio_recorder_service.dart`.
- Recordings queue stores audio as SQLite BLOB — fine at research volumes, but revisit
  (store file path + move blob to filesystem) before large-scale field collection.
- Auth is local (salted SHA-256, single-row session) — replaced by backend auth in M3.
- Auth gating is done in the auth screen (restore-session on start), not a go_router
  `redirect` — revisit when real auth lands.
