---
name: flutter-development
description: "Use when building Flutter/Dart apps. Architecture + gotchas."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [flutter, dart, riverpod, go_router, dio, record, mobile, offline-first]
    related_skills: [kotlin-mobile-development, technical-mentorship-workflow, systematic-debugging]
---

# Flutter Development

## Overview

Governs Flutter/Dart app work: layered architecture, Riverpod state, offline-first data
flow, audio capture, browser preview, and the Windows toolchain. Calibrated against the
GhaLingo Flutter rebuild (`ghalingo_flutter`, package `com.ghanaspeech`) — the Flutter
re-implementation of the Kotlin collector, targeting the same Express backend and
openapi.yaml contract.

## When to Use

- Building or modifying a Flutter app (widgets, Riverpod, go_router, dio, record, local DB).
- Reviewing/refactoring a Flutter codebase for architecture or sync reliability.
- Adding screens, models, endpoints, or providers to a Flutter project.
- Debugging Flutter build, web-preview, or package-API issues.
- Working on the GhaLingo Flutter repo (`C:\Users\bohen\Documents\Hermes\ghalingo_flutter`):
  load `references/ghalingo-flutter.md` for paths, contract facts, and milestone state.

**Don't use for:** Kotlin/Android work (see `kotlin-mobile-development`), Express/TS
backend work, Flutter package publishing, or ADB TV control (`android-tv-adb-control`).

## Stack Conventions (GhaLingo Flutter reference)

| Concern | Choice | Why |
|---|---|---|
| UI | Widgets + Material 3 | Standard, theme via ColorScheme.fromSeed |
| Navigation | go_router (static route table) | Declarative, type-safe; `extra` carries typed args |
| State | Riverpod 2.6 `Notifier` / `AsyncNotifier` | Closest analog to Kotlin StateFlow/ViewModel |
| DI | ProviderScope + `Provider`/`NotifierProvider` | Scoped singletons, overridable in tests |
| Network | dio + interceptor (auth header + debug logging) | Retrofit/OkHttp analog |
| Auth token | `TokenStore` provider read by a dio interceptor | Repository stays auth-agnostic |
| Audio | `record` (web=MediaRecorder webm; mobile=native 16 kHz WAV) | See pitfall 8 |
| Local DB | sqflite (mobile) + sqflite_common_ffi_web (web) | single databaseFactory switch; see pitfall 9 |
| Build | Flutter 3.35.7 / Dart 3.9.2 (stable) | on PATH (see Toolchain) |

## Architecture Rules

Layered folders under `lib/`; UI never touches dio directly:

```text
core/        # config (dart-define flags), theme, network (dio + token interceptor), router, errors
data/
  models/    # wire DTOs (manual fromJson, snake_case keys)
  remote/    # typed dio client (one class per API surface)
  repository/ # abstract interface + real impl + fake impl + providers
audio/       # recorder service wrapper
ui/
  controllers/ # Riverpod Notifier/AsyncNotifier view models (one State/AsyncValue per screen)
  screens/     # feature screens (ConsumerWidget/ConsumerStatefulWidget)
  widgets/     # shared (AsyncValueView for loading/error/data)
```

- `main.dart` holds only `ProviderScope` + `MaterialApp.router` (+ `device_preview` guard).
- Every screen consumes a controller; no business logic in widgets.
- UI depends on the repository **interface**, never dio/`SpeechApi` directly.
- Fake repository + a `bool.fromEnvironment('USE_FAKE_API', defaultValue: true)` flag lets
  the app run backend-less during dev; flip to `false` when the real API is wired.

## Toolchain Facts (this machine)

- Flutter 3.35.7 stable @ `C:\Users\bohen\Documents\adf\flutter_windows_3.35.7-stable\flutter\bin`;
  both `flutter` and `dart` are on PATH in the Hermes bash shell.
- Web builds (`flutter build web` / `flutter run -d chrome`) need **no** JDK or Android SDK
  — only android/ios targets do.
- `flutter create` does **not** run `git init`; init manually before the first commit.

## Build & Run

```bash
cd /c/Users/bohen/Documents/Hermes/ghalingo_flutter
flutter analyze
flutter test
flutter build web
flutter run -d chrome --web-port=8080                          # browser preview (debug)
flutter run -d chrome --web-port=8080 --dart-define=USE_FAKE_API=false  # hit real backend
```

`--dart-define` flags (API_BASE_URL, USE_FAKE_API) are compile-time constants — changing
them requires a restart, not hot reload.

## Common Pitfalls (each verified by a real failure)

1. **record 5.x `start()` requires a non-null `path`.** Signature is
   `start(RecordConfig config, {required String path})`; web ignores `path` but still
   requires it. Pass `''` on web, a temp `.wav` path on mobile. Passing `String?` → compile error.
2. **Riverpod 2.6 family notifier base class.** For `AsyncNotifierProvider.family`, the
   controller extends `FamilyAsyncNotifier<State, Arg>` (NOT `AsyncNotifier`) and its
   `build(Arg arg)` takes the family argument. `ref.invalidateSelf()` returns **void** —
   declare reload helpers as `void reload() => ref.invalidateSelf();`, not `Future<void>`.
3. **dio raw octet-stream body.** For binary bodies use
   `data: Stream.fromIterable([Uint8List.fromList(bytes)])` + `Options(contentType: 'application/octet-stream')`.
   A bare `List<int>` can be mistaken for a JSON array and get json-encoded.
4. **device_preview needs BOTH pieces.** Wrap with `DevicePreview(enabled: kDebugMode,
   builder: (_) => app)` AND set `builder: DevicePreview.appBuilder` on `MaterialApp`.
   Put `device_preview` in `dependencies` (not dev_dependencies) or analyzer flags
   `depend_on_referenced_packages`.
5. **Flutter web renders to a `<canvas>`** — no accessibility/AX elements, so GUI
   automation (computer_use) must click by pixel coordinates, not element index.
6. **`flutter run -d chrome` in background leaves an orphan on the port.** Killing the
   `flutter run` process leaves a `dart.exe` still LISTENING. Free it with
   `netstat -ano | grep :8080` to get the PID, then
   `powershell -NoProfile -Command "Stop-Process -Id <pid> -Force"`. (`taskkill //PID`
   mangles under git-bash — use the PowerShell route.)
7. **`flutter analyze`/`flutter test` are not auto-detected** by the verification harness.
   To produce unambiguous evidence, write a throwaway `hermes-verify-*.sh` under Temp that
   runs both, run it, then `rm` it.
8. **Web audio is webm/opus, not research WAV.** Browsers only expose MediaRecorder, so
   16 kHz / 16-bit PCM mono WAV is a **mobile-only** capture path. Treat web recording as a
   dev-preview convenience and document it as such in the recorder service.
9. **sqflite is mobile-only — pair it with `sqflite_common_ffi_web` for web.** One
   `DatabaseFactory` switch (`kIsWeb ? databaseFactoryFfiWeb : databaseFactory`) keeps a
   single SQL codebase across targets. Use `getDatabasesPath()` (sqflite) for the mobile
   path and a virtual `'ghalingo.db'` name on web. Caveat: `sqflite_common_ffi_web` loads
   `sqlite3.wasm` from a CDN by default — bundle the wasm in `web/assets` for a truly
   offline web build.
10. **Persisting web audio needs bytes, not the blob URL.** `record` 5.x `stop()` returns a
    `blob:` URL on web (ephemeral, gone on reload) vs a real file path on mobile. To store
    offline, read bytes through a **conditional import**: `dart:io File(path).readAsBytes()`
    on mobile, `dart:html HttpRequest.request(path, responseType: 'arraybuffer')` then
    `.response.asUint8List()` on web. Use `if (dart.library.io) … if (dart.library.html) …`
    imports so neither `dart:io` nor `dart:html` leaks into the wrong build.

## Verification Checklist

- [ ] `flutter analyze` → "No issues found".
- [ ] `flutter test` green (models pin snake_case wire shapes; controllers pin state wiring).
- [ ] Model `fromJson` keys match openapi.yaml exactly (grep `SpeechApi`/models vs the contract).
- [ ] `USE_FAKE_API` default is deliberate (true during dev, false before release).
- [ ] `flutter build web` succeeds after dependency/signature changes.

## One-Shot Recipes

**Add a screen:** create `ui/screens/<feature>/<feature>_screen.dart` (ConsumerWidget) →
create a controller (Notifier/AsyncNotifier) → add a `GoRoute` (pass typed args via `extra`).

**Add a model:** data class + `fromJson` reading snake_case keys → seed a `fromJson` test.

**Add an endpoint:** add a method on the dio client (path carries full `api/v1/...` prefix)
→ wrap in the repository interface + real impl + fake impl.

**Add a provider:** `Provider`/`NotifierProvider` in `data/repository/providers.dart` or
`ui/controllers/`, then `ref.watch`/`ref.read` in the widget.
