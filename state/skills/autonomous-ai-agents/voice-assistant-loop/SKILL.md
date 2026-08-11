---
name: voice-assistant-loop
description: "Use when building voice loops: wake word, STT, Hermes, TTS."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [voice, stt, tts, wake-word, whisper, jarvis, audio, windows]
    category: autonomous-ai-agents
---

# Voice Assistant Loop (Jarvis-style)

Build a hands-free voice round-trip on this Windows PC: wake word → mic
record → speech-to-text → Hermes → text-to-speech → speaker. Fully offline
for the speech parts; the brain is `hermes chat -q` (no gateway needed).

## When to Use

- User asks to build/extend a voice assistant ("Jarvis", "voice control",
  "talk to the AI", "wake word").
- Debugging the existing loop at `C:\Users\bohen\jarvis\jarvis.py`.
- Wiring mic/STT/TTS for any other voice project on this machine.

## Architecture (verified Aug 2026)

```
Mic (sounddevice) → WakeWord (openwakeword) → Record w/ silence-end
→ faster-whisper (STT) → hermes chat -q -Q --resume <id>
→ edge-tts (TTS, mp3) → miniaudio playback → Speaker
```

## Environment (this PC)

- Project: `C:\Users\bohen\jarvis\` — `.venv` + `jarvis.py` + `mic_check.py`.
- Deps installed in `.venv`: `faster-whisper sounddevice openwakeword
  edge-tts numpy miniaudio` (`uv pip install --python ./.venv/Scripts/python.exe …`).
- **Real input mic = Microphone Array (Realtek(R) Audio) — resolved BY NAME,
  NEVER by device id.** Windows MME device ids renumber between sessions: the
  Realtek was device 5 at build time, then device 1 after Iriun's virtual
  webcam mics re-registered. `jarvis.py` has `resolve_mic()` which scans
  `sd.query_devices()` for `MIC_NAME_PATTERN = "Microphone Array (Realtek"`,
  falls back to the system default. `--mic <id>` remains an explicit
  override (e.g. a headset). The Iriun webcam "microphones" read true zeros
  unless the Iriun app is feeding audio — never pick them as default.
  Voicemeeter virtual devices present too.
- **OS default input is ALSO the Realtek Array** (verified via Core Audio
  `GetDefaultAudioEndpoint`: CAPTURE-Console AND CAPTURE-Comm roles) — name
  resolution is belt-and-braces, the flag is not required. Watch for drift:
  if Iriun ever grabs the default role, Jarvis goes dead-silent with repeated
  `[no speech detected]`. Re-verify the ACTUAL default with
  `scripts/get_default_audio.ps1` (Core Audio) — and re-resolve the mic at
  runtime, never trust a device id recorded in an earlier session.
- Output: default speakers via miniaudio (device auto).
- **PYTHONPATH pollution when launching inside a Hermes session**: the
  parent env injects `…\hermes-agent` and `…\hermes-agent\venv\Lib\site-packages`
  AHEAD of the project venv, so `import numpy` resolves from the WRONG
  venv. `run.cmd` now clears it itself (`set PYTHONPATH=` right after
  `cd /d`), so `.\run.cmd …` is always safe; a raw
  `PYTHONPATH= ./.venv/Scripts/python.exe jarvis.py …` invocation in a
  hand-typed command still needs the explicit clear.

## Hermes integration (the critical call)

```python
subprocess.run(["hermes", "chat", "-q", prompt, "-Q", "--resume", sid],
               capture_output=True, text=True, timeout=180)
```

- `-q <text>` = one-shot query. `-Q` = quiet/programmatic (no banner/spinner).
- **Session continuity = resume by ID, NOT `--continue <name>`.** A named
  resume fails on first use: `No session found matching 'jarvis'`. Correct
  pattern: keep the session ID in a `.session_id` file next to the script;
  omit `--resume` on the first run, then parse the **stderr** line
  `session_id: <id>` (it is NOT on stdout) and persist it; subsequent calls
  pass `--resume <id>`.
- stdout = reply + footer block. Strip the footer: lines starting
  `Model:` / `Platform:` / `Session:` and the literal "What are we working on?".
- Latency on the free model ≈ **19 s/query** — say so when setting
  expectations; a faster model shrinks it dramatically.

## Key API facts (each one cost debugging time)

- **faster-whisper transcribes MP3 directly** (PyAV bundled) — no ffmpeg
  needed; feed the edge-tts mp3 straight in. Base model, `int8` on CPU.
  First run downloads the model (~1 min) — warm it before going live.
- **edge-tts** → outputs **MP3** (e.g. `en-US-GuyNeural`).
- **Windows `Media.SoundPlayer` only plays WAV** — an mp3 throws
  "not a valid wave file". Do NOT route playback through PowerShell
  SoundPlayer with mp3.
- **miniaudio 1.71**: `play_file()` was REMOVED; `PlaybackDevice.start()`
  REQUIRES the callback generator arg. Working pattern:
  ```python
  import miniaudio
  with miniaudio.PlaybackDevice(output_format=miniaudio.SampleFormat.SIGNED16,
                                sample_rate=44100, nchannels=2) as dev:
      dev.start(miniaudio.stream_file(str(mp3)))   # blocks until done
  ```
- **openwakeword**: ships an offline `jarvis` wake-word model — instant
  Stark vibe, no API key. `Model(wakeword_models=[word])`; threshold ~0.5.
- Recording: 16 kHz mono float32, 0.2 s blocks; end utterance on ~0.8 s of
  trailing silence AFTER first speech is heard; keep ~0.4 s lead-in before
  the first speech chunk. VAD threshold = **linear RMS amplitude**, never
  RMS dB: float audio dB is always ≤ 0 (speech ≈ −20…−40 dB), so a positive
  dB cutoff flags ALL audio as silence and ends recordings in ~1 s.
- **Calibrate the VAD, don't hardcode** — measured at user's normal sitting
  distance: speech 0.0057–0.037 RMS, noise peaks ~0.0045. Working settings
  from that data: `SILENCE_RMS = 0.004` + `SPEECH_CONFIRM_CHUNKS = 2`
  (requires 2 consecutive speech chunks, so a single noise blip can't open
  the recording window). Use `--levels N` live meter while talking
  from the real position; tell speech apart from noise, set the threshold
  mid-gap, and confirm ≥2 when the gap is thin. Use the live meter
  (`--levels N`, mic auto-resolved by name) while talking from the real
  position.
- **If the speech/noise gap is thin, the real fix is mic gain, not
  threshold gymnastics** — boosting the Realtek Array +20 dB in Windows
  (`mmsys.cpl` → Recording → Properties → Levels) widens the gap ~10× and
  makes whisper more accurate. Threshold tuning can't fix a mic that's
  fundamentally too quiet.

## Noise reduction (verified Aug 2026)

When the user asks to "lower the noise floor", MEASURE FIRST. On this rig
the steady room noise was only RMS 0.00017 (−75 dB) — the real problem was
weak voice signal (0.008 RMS at sitting distance), not noise. Characterize
with a quiet-room recording + per-band FFT; only add DSP that a measured
test proves.

Validated with a clean rig (known speech + real noise → whisper):
- **`noisereduce` spectral gating works**: residual noise −70%, Whisper
  char-accuracy 67% → 98% (`nr.reduce_noise(y=audio, sr=SR, y_noise=profile,
  prop_decrease=0.9)`). Only apply when the captured noise floor is actually
  noisy (skip if < ~0.0005 RMS — gating a quiet room adds artifacts).
- **High-pass / butter filters HURT at these amplitudes** (filter ringing
  scrambled whisper to 20% accuracy). Do NOT add high-pass to the chain.
- **Whisper `vad_filter=True`** helps (drops non-speech segments).
- **Noise-profile capture must discard the first buffer** (MME quirk) so the
  reference isn't garbage → NaN.

## Deterministic testing (no human needed)

Validate STT/TTS without a live speaker: **generate known audio with
edge-tts, then transcribe it with whisper**. If the transcript matches the
prompt, the speech chain is proven; the only remaining variable is mic
pickup level. Example: `edge_tts.Communicate("Turn on the lights", …).save()`
→ `WhisperModel("base").transcribe(mp3)` → expect the same words.

## Pitfalls

- **PowerShell does NOT search the CWD for executables** (unlike cmd): a
  bare `python.exe` run from `.venv\Scripts` resolved to the uv base Python
  (no miniaudio) → `ModuleNotFoundError: miniaudio`. Launch via `run.cmd`
  in the project dir, which `cd /d`'s and calls
  `.venv\Scripts\python.exe jarvis.py %*`.
- Splat-style argument passing: pass args unpacked, not as one list/tuple.
- **cmd.exe batch files are ASCII + CRLF only.** A `run.cmd` written with a
  UTF-8 em-dash in a comment (or LF-only line endings) fails with a cryptic
  `'M' is not recognized` on launch — cmd misparses multibyte UTF-8 and LF
  endings. Keep `.cmd`/`.bat` comments pure ASCII and rewrite with `\r\n`.
- MSYS path mangling: native Windows python wants `C:\...` paths, not
  `/c/...` — `/tmp/...` in a heredoc can silently land in `C:\tmp`.
- **Testing a `.cmd` launcher from git-bash: `cmd //c "run.cmd …"` mangles
  the flags (MSYS converts `//c` to `/c` oddly) and prints a bare
  `Microsoft Windows [Version …]` banner without executing the batch. Run it
  via PowerShell instead:
  `powershell -NoProfile -Command "cmd /c run.cmd --list-devices"` — or `cd`
  into the project dir and call the batch directly.
- **MME first-read garbage**: the very first `sd.rec()`/`InputStream.read()`
  on Windows MME can return uninitialized data (huge values → NaN RMS).
  Always discard a ~0.5 s warmup buffer before capturing a noise profile or
  a real utterance.
- **Stereo-interleave trap in test rigs**: edge-tts mp3s decode as
  **2-ch/44.1 kHz interleaved** L/R. `np.frombuffer(dec.samples)` then
  treats L/R pairs as adjacent mono samples, scrambling speech. Check
  `dec.nchannels`; downmix with `buf[0::2]` (or average channels) BEFORE
  resampling. A corrupted mix makes whisper output look like the DSP failed
  — validate the rig on noise-free known audio first.
- Wake-word loop prints `[waiting for 'jarvis'...]` — test with
  `--cli` (Enter-to-talk) first, then hands-free.
- `--once` for a single utterance; `--list-devices` to enumerate mics.

## Verification checklist

1. `mic_check.py 3` while speaking → peak > 0.02 (voice level, not ambient).
2. Known-audio round-trip: TTS prompt → whisper transcript matches.
3. `hermes chat -q "Say OK" -Q` returns text; first run persists the
   stderr `session_id:` into `.session_id`; a second run resumes it.
4. `speak("…")` plays through the speakers (miniaudio, mp3).
5. Full `jarvis.py --cli --once` → speak, hear reply (mic auto-resolved;
   `--mic <id>` only for override).

See `references/voice-loop-build.md` for the session build transcript
with exact commands and error→fix pairs.