---
name: flutter-mobile-development
description: "Use when developing Flutter/Dart apps, mobile or web."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [flutter, dart, mobile, web, riverpod, go-router, dio, offline-first, audio-recording]
    related_skills: [kotlin-mobile-development, technical-mentorship-workflow, test-driven-development, systematic-debugging]
---

# Flutter / Dart Mobile & Web Development

## Overview

Governs Flutter/Dart application work: architecture, offline-first patterns, data-layer
design, audio capture, and the toolchain. Calibrated against the GhaLingo Flutter rebuild
(`ghalingo_flutter`), the concrete reference project for conventions and pitfalls. It is the
Flutter counterpart of `kotlin-mobile-development` (same GhaLingo product, different client).

The goal is production-quality, maintainable Flutter code: modular layers, explicit
contracts, reliable sync, runtime-safe permissions, testable units — not prototype-in-one-file UI.

## When to Use

- Building or modifying a Flutter/Dart app (Riverpod, go_router, dio, etc.).
- Reviewing/refactoring a Flutter codebase for architecture, sync reliability, or security.
- Adding screens, models, dio endpoints, repositories, or Riverpod providers.
- Debugging Flutter build/analyze/runtime issues (including web-in-browser dev).
- Working on the GhaLingo Flutter repo (`C:\Users\bohen\Documents\Hermes\ghalingo_flutter`):
  load `references/ghalingo.md` for project paths, contract facts, and current state.

**Don't use for:** Kotlin/Android work (see `kotlin-mobile-development`), backend API design
(Express), or Android TV control via ADB (see `android-tv-adb-control`).

## Stack Conventions (GhaLingo reference)

| Concern | Choice | Why |
|---|---|---|
| State | Riverpod 2.x (`Notifier`/`AsyncNotifier`/`FamilyAsyncNotifier`) | Observable state + DI, closest Flutter analog to Kotlin StateFlow/ViewModel |
| Navigation | go_router (declarative, static route table) | Type-safe, single-activity analog; pass objects via `extra` |
| Networking | dio + debug-only `LogInterceptor` | Retrofit/OkHttp analog; interceptors for auth + logging |
| Local DB | (deferred — see offline-first section) | Repository is abstracted so the choice lands later without UI churn |
| Audio | `record` package behind a service interface | Mobile → 16 kHz/16-bit PCM WAV; web → MediaRecorder (dev-preview only) |
| Mobile preview | `device_preview` (kDebugMode guard) | Phone frame in the browser |
| Auth token | in-memory `TokenStore` + dio interceptor | Secure storage (flutter_secure_storage) lands with real auth |

## Architecture Rules

Layered folders under `lib/`; UI never touches dio/DB directly:

```text
core/config/     # AppConfig (compile-time --dart-define constants)
core/network/    # dio client, TokenStore, error mapping
core/router/     # go_router table (+ route payload types)
core/theme/      # Material 3 theme
data/models/     # wire DTOs with manual fromJson (snake_case keys)
data/remote/     # thin typed dio wrapper (SpeechApi)
data/repository/ # interface + impl + fake + providers (single source of truth)
audio/           # recorder service abstraction
ui/controllers/  # Riverpod Notifiers (view-model role)
ui/screens/      # one folder per screen
ui/widgets/      # shared (e.g. AsyncValueView for loading/error/data)
```

Completion criteria:
- `main.dart` only assembles `ProviderScope` + `MaterialApp.router` (+ device_preview guard).
- Every screen reads a provider; no business logic in `build`; no hardcoded data in UI
  (demo data lives in the fake repository).
- Models map wire snake_case → Dart camelCase explicitly in `fromJson` (no codegen required).

## Build & Test Commands

Windows shell is git-bash (POSIX). Flutter 3.35.7 stable + `dart` are on PATH
(`C:\Users\bohen\Documents\adf\flutter_windows_3.35.7-stable\flutter\bin`). No JDK needed
for web builds — the Android SDK/JDK only matter for `flutter build apk`.

```bash
cd flutter-project
flutter analyze                 # static analysis (fast, run after every edit)
flutter test                    # unit + widget tests
flutter build web               # release dart2js compile check (~60s)
flutter run -d chrome --web-port=8080   # dev server + hot reload; long-lived process
```

**Verification note:** Flutter has no npm/pytest/make-equivalent that harnesses auto-detect.
`flutter analyze`, `flutter test`, and `flutter build web` ARE the canonical checks — run them
explicitly and cite their output as verification evidence.

## Common Pitfalls (all hit + fixed against GhaLingo Flutter, Aug 2026)

1. **`record` 5.x `start()` requires a non-null `path`.** Signature is
   `Future<void> start(RecordConfig config, {required String path})` — the path is *ignored*
   on web but still required. Pass `''` on web, temp-dir `.wav` on mobile. Passing a `String?`
   fails analyze with `argument_type_not_assignable`.
2. **Riverpod 2.x family notifier base is `FamilyAsyncNotifier`, not `AsyncNotifier`.**
   For a `.family` provider the notifier extends `FamilyAsyncNotifier<State, Arg>` with
   `build(Arg arg)`. Overriding `AsyncNotifier.build()` with a `build(int)` signature throws
   `invalid_override` / `type_argument_not_matching_bounds`. Provider:
   `AsyncNotifierProvider.family<NotifierT, State, Arg>(NotifierT.new)`. Non-family uses plain
   `AsyncNotifier<State>` with `build()`.
3. **`ref.invalidateSelf()` returns `void`.** A `reload()` helper must be `void reload() =>
   ref.invalidateSelf();` — declaring `Future<void> reload() => ref.invalidateSelf();` throws
   `return_of_invalid_type`.
4. **`device_preview` must be a regular `dependency`, not `dev_dependency`.** Importing it from
   `lib/main.dart` while it's in `dev_dependencies` triggers `depend_on_referenced_packages`
   (info). Also require `enabled: kDebugMode` on the `DevicePreview` widget AND
   `builder: DevicePreview.appBuilder` on `MaterialApp` (without the latter the frame never
   renders).
5. **dio raw-bytes upload.** To send `application/octet-stream`, pass
   `data: Stream.fromIterable([Uint8List.fromList(bytes)])` + `Options(contentType: 'application/octet-stream')`.
   A bare `List<int>` body risks being JSON-encoded (dio treats `List` as JSON array). This is
   the shape for the chunked `uploads/chunk` route.
6. **Web audio recording is not research-grade.** Browsers give MediaRecorder (webm/opus);
   16 kHz/16-bit PCM WAV is mobile-only. `record`'s `onAmplitudeChanged` stream is not available
   on web — guard amplitude subscription with `kIsWeb`. Web capture is a dev-preview path.
7. **Flutter web renders to a single `<canvas>`** → no DOM/AX elements. `computer_use` element-index
   clicking and `type` will not reach canvas inputs; only pixel coordinates land, and keyboard
   input requires a click-to-focus first. Don't fight this for UI verification — write a
   controller/widget test instead (see recipes).
8. **`FontFeature.tabularFigures()` is available via `package:flutter/material.dart`** (re-exported
   from `dart:ui`) — no separate `dart:ui` import needed.
9. **snake_case wire contract.** GhaLingo's backend is snake_case with ONE quirk:
   `ValidationResult.isValid` is camelCase on the wire. Map fields explicitly in `fromJson`; keep
   a contract test that pins these shapes so drift breaks at test time, not runtime.

## Offline-First Sync Pattern (milestone 2+)

Same discipline as the Kotlin client — write local first (`pending` status), sync via background
worker, cap retries, persist upload-session state, delete local files only after server-confirmed
success, never leave zombie `pending` rows. The Flutter data layer is already abstracted behind a
repository interface so a Drift/Hive/sembast store slots in without touching the UI.

## One-Shot Recipes

**Add a screen:** (1) `ui/screens/<feature>/<feature>_screen.dart` (stateless, reads providers);
(2) controller `Notifier`/`AsyncNotifier` in `ui/controllers/`; (3) register route in
`core/router/app_router.dart`; (4) navigate with `context.push(path, extra: payload)`.

**Add a model:** add `fromJson` in `data/models/`, add a contract test in `test/` pinning the
snake_case (and any camelCase quirk) keys.

**Add a dio endpoint:** (1) add typed method on `data/remote/speech_api.dart`; (2) add the same
method to `data/repository/speech_repository.dart` (interface) + impl + fake; (3) wire a controller.

**Verify a controller's runtime wiring without a browser:** unit-test the notifier with
`ProviderContainer(overrides: [repoProvider.overrideWithValue(FakeRepo())])`, drive login/state
methods, assert state + TokenStore. This is the robust substitute for browser click-through
(which Flutter-web canvas defeats).

## Verification Checklist

- [ ] `flutter analyze` clean.
- [ ] `flutter test` green (contract tests + controller tests exist).
- [ ] `flutter build web` succeeds for web targets (or `flutter build apk` for Android).
- [ ] Models map the exact wire field names (snake_case, plus the `isValid` camelCase quirk).
- [ ] Logging is debug-only and never prints the Authorization header.
- [ ] No `useFakeApi`/fake data leaking into a release build (`USE_FAKE_API` flip is explicit).
- [ ] Recorder path handling matches the record-5 `required path` signature ('' on web).

See `references/ghalingo.md` for the GhaLingo Flutter project state.
