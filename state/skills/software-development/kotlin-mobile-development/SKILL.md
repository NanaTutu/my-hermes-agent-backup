---
name: kotlin-mobile-development
description: "Use when developing Kotlin Android apps: offline-first sync."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [kotlin, android, jetpack-compose, room, retrofit, workmanager, hilt, mobile, offline-first]
    related_skills: [technical-mentorship-workflow, test-driven-development, systematic-debugging]
---

# Kotlin Android Mobile Development

## Overview

This skill governs Kotlin/Android application work: architecture, offline-first patterns, data-layer design, audio capture, and the Gradle toolchain. It is calibrated against the GhaLingo speech-collection app (`com.ghanaspeech.collector`), which serves as the concrete reference project for conventions and pitfalls.

The goal is production-quality, maintainable Android code: modular layers, explicit contracts, reliable sync, runtime-safe permissions, and testable units — not prototype-in-one-file UI.

## When to Use

- Building or modifying an Android app in Kotlin (Compose, Room, Retrofit, WorkManager, Hilt).
- Reviewing or refactoring an existing Kotlin Android codebase for architecture, sync reliability, or security.
- Adding screens, Room entities/DAOs, Retrofit endpoints, Workers, or Hilt modules.
- Debugging Android build, networking, permission, or background-sync issues.
- Mentoring Kotlin/Android development for Tutu (pair with `technical-mentorship-workflow`).
- Working on the GhaLingo repo (`C:\Users\bohen\Documents\Hermes\GhaLingo`): load `references/ghalingo.md` for project paths, API contract facts, known defects, and fix order — verify state against code, don't trust it blindly.

**Don't use for:** backend API design (Express), Flutter/Dart mobile work, or Android TV control via ADB (see `android-tv-adb-control`).

## Stack Conventions (GhaLingo reference)

| Concern | Choice | Why |
|---|---|---|
| UI | Jetpack Compose + Material 3 | Declarative, testable semantics |
| Navigation | Navigation-Compose, single-activity | Simple back stack, no fragments |
| State | ViewModel + StateFlow/UiState | Survives config changes, testable |
| Local DB | Room (SQLite) | Offline-first cache, Flow queries |
| Key-value | DataStore Preferences | Replaces SharedPreferences |
| Network | Retrofit + OkHttp + Gson/Moshi | Standard, interceptors for logging/auth |
| Background | WorkManager (CoroutineWorker) | System-managed retries/exponential backoff |
| DI | Hilt (kapt) | Scoped singletons, worker injection |
| Audio | AudioRecord + raw WAV (16-bit PCM mono, 16 kHz) | Research-grade ASR format |
| Build | AGP 8.5.1, Kotlin 2.0.20, JDK 17, minSdk 23, targetSdk 34 | Check `app/build.gradle` for current pins |

## Architecture Rules

Layered folders under the package root; UI never touches Room/Retrofit directly:

```text
ui/          # screens, components, theme, navigation; ViewModels own screen state
domain/      # models + use cases (add when logic exceeds repository passthrough)
data/local/  # Room entities, DAOs, AppDatabase
data/remote/ # Retrofit interface + DTOs, request/response models
data/repository/  # single source of truth coordinating cache + network
data/sync/   # WorkManager workers
audio/       # recorder + technical validation
di/          # Hilt modules (database, network, api, repository)
```

Completion criteria for architecture changes:

- `MainActivity` contains only `setContent { AppNavigation() }` and theme setup.
- Every screen has a paired ViewModel exposing `StateFlow<UiState>`; no business logic in composables.
- Screens consume repository Flows; no hardcoded demo data in UI (move to Room seed or fake repository in tests).
- One file, one responsibility: a file over ~250 lines of mixed concerns is a refactor trigger.

## Offline-First Sync Pattern

1. **Write local first**: save recording + metadata to Room (status `pending`) immediately; never require network for the core flow.
2. **Sync via WorkManager**: `CoroutineWorker` reads `pending` rows, uploads each, marks `uploaded` with server id/url.
3. **Retry with bounds**: on failure increment `retryCount`; give up (status `failed`) after a hard cap (e.g. 5).
4. **Persist upload session state**: an in-memory `uploadId` dies with the process. Persist session id + chunk index (Room column or DataStore) so a restart resumes instead of restarting the whole file.
5. **Clean up disk**: after successful upload + server confirmation, delete local WAV files (with an age guard — never delete the same batch the device is still verifying).
6. **Handle missing files**: if the local WAV is gone before upload, delete the Room row or mark `failed` — do not silently `return@forEach` leaving a zombie `pending` row.
7. Add constraints where it matters: `Constraints(NetworkType.CONNECTED)` for uploads; periodic sync for mission/prompt refresh.

## Audio Capture Rules (WAV)

- 16-bit PCM, mono, 16,000 Hz, `AudioFormat.ENCODING_PCM_16BIT`.
- Write a 44-byte header first, patch sizes on stop (never trust `length()` mid-write).
- `stopRecording()` must: set `isRecording = false`, `join()` the writer thread, then `stop()`/`release()` `AudioRecord`. Releasing before the thread finishes corrupts the header.
- Validate on-device after capture: silence %, clipping count, peak amplitude, SNR estimate, duration bounds, file size > 44 bytes. Never judge accent/language correctness — physical signal features only.
- Request `RECORD_AUDIO` (and `ACCESS_FINE_LOCATION`, if GPS is used) at runtime with explicit explanation, and degrade gracefully when denied. Never suppress `MissingPermission` and call `startRecording()` anyway.

## Build & Test Commands

Windows shell is git-bash (POSIX syntax). `java` may be absent from a bare shell — locate JDK 17 or set `JAVA_HOME` first:

```bash
export JAVA_HOME="/c/Program Files/Android/Android Studio/jbr"   # or your JDK 17 path
cd android-project
./gradlew assembleDebug        # build APK
./gradlew testDebugUnitTest    # JVM unit tests
./gradlew connectedAndroidTest # instrumented tests (device/emulator required)
./gradlew lint                 # Android lint + build checks
./gradlew app:dependencies --configuration debugRuntimeClasspath  # verify dep tree
```

Debug vs release: debug build should be the only variant with `HttpLoggingInterceptor.Level.BODY` and `applicationIdSuffix ".debug"`. Release: R8/minify on, BODY logging off.

## Common Pitfalls

1. **Retrofit baseUrl doubled with path prefix.** `baseUrl("https://api.example.com/api/v1/")` + `@GET("api/v1/missions")` → `.../api/v1/api/v1/missions`. Decide once: either baseUrl ends at host and annotations carry full path, or baseUrl includes the version prefix and annotations are relative (`"missions"`).
2. **camelCase DTOs vs snake_case server JSON.** Gson maps by field name; `promptId` never matches `prompt_id`. Options: annotate (`@SerializedName("prompt_id")`), or mandate one convention and enforce it with contract tests. Verify JSON contract against the actual backend before writing the client.
3. **BODY logging in production builds.** Logs tokens, emails, GPS, audio metadata. Gate behind `BuildConfig.DEBUG`.
4. **`allowBackup="true"` with tokens/recordings/GPS on device.** Review backup rules (`android:fullBackupContent` / `dataExtractionRules`) or set `allowBackup="false"` for sensitive-data apps.
5. **`@SuppressLint("MissingPermission")` on record start.** Compiles, crashes at runtime on API 23+ without the runtime grant. Implement permission flow first.
6. **Room `exportSchema = false`.** Fine for prototypes; before release set `exportSchema = true`, commit schemas, and add `Migration`s instead of bumping `version` and wiping user data.
7. **Non-joined recorder threads.** Releasing `AudioRecord` while the writer thread still runs → truncated/corrupt WAV. Join before release.
8. **Silent failure on missing upload file.** `if (!file.exists()) return@forEach` leaves a `pending` row forever. Delete the row or mark `failed` explicitly.
9. **Upload session state kept only in RAM.** Process death mid-upload loses `uploadId`; chunks uploaded to a dead session are garbage. Persist session metadata.
10. **Hardcoded missions/prompts in composables** for demo purposes. It works visually, but every entity must come from the repository once a backend exists — keep demo data in `remember` only until the data layer is wired, and remove it before release.
11. **Whole-file retry instead of chunk resume.** "Retry the chunk" (docs) vs "restart the upload" (code) are different. If chunks exist, index must be resumable, not 0-based re-send.
12. **MD5 computed client-side but never validated server-side.** Either validate on the backend or drop the field — computing it is wasted battery otherwise.

## Verification Checklist

- [ ] `./gradlew assembleDebug` succeeds (JDK 17 configured).
- [ ] `./gradlew testDebugUnitTest` passes (or tests exist and are wired).
- [ ] No `@SuppressLint("MissingPermission")` without a runtime permission flow guarding the call.
- [ ] Retrofit baseUrl + all endpoint paths produce exactly one `api/v1`-style prefix (grep the interface and the DI module).
- [ ] DTO field names match the actual backend JSON (annotations applied where the contract differs).
- [ ] BODY logging is debug-only.
- [ ] `allowBackup` / backup rules reviewed for sensitive data.
- [ ] Room `exportSchema` decision made; migrations added for version bumps.
- [ ] Recorder `stopRecording()` joins its writer thread before releasing `AudioRecord`.
- [ ] Sync worker handles missing files, persists session state, and caps retries.
- [ ] Screens source data from ViewModels/repositories, not hardcoded lists.
- [ ] Pending uploads cleanup deletes local files only after server-confirmed success (with age guard).

## One-Shot Recipes

**Add a screen:**
1. Create `ui/screens/<Feature>/<Feature>Screen.kt` (stateless composables, takes state + lambdas).
2. Create `<Feature>ViewModel.kt` exposing `StateFlow<UiState>`; constructor injects repository.
3. Register route in `AppNavigation` NavHost + `composable("feature")`.
4. Wire navigation with explicit arguments (no `Bundle`-less string parsing where types exist).
5. Add a Compose UI test asserting title + primary action.

**Add a Room entity:**
1. Add `@Entity` data class in `data/local/`.
2. Add DAO interface with suspend/Flow methods; CRUD via repository only.
3. Add to `@Database(entities = [...])` list.
4. Bump version + add `Migration` (exportSchema must be on).
5. Test: DAO round-trip with Room in-memory database (`Room.inMemoryDatabaseBuilder`).

**Add a Retrofit endpoint:**
1. Define DTOs matching the backend contract exactly (annotations for snake_case if needed).
2. Add suspend method on the Retrofit interface.
3. Add repository method wrapping it with error handling (`Result` type or sealed UiState).
4. Verify against real backend with a contract test or manual request before UI wiring.

**Add a background job:**
1. `@HiltWorker` CoroutineWorker + `@AssistedInject` constructor.
2. Register with WorkManager (one-time or periodic) in repository/application code.
3. Set constraints (network) where applicable; cap retries explicitly.
4. Test with `TestListenableWorkerBuilder` + MockWebServer.