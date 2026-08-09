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
→ faster-whisper (STT) → hermes chat -q -Q --continue SESSION
→ edge-tts (TTS, mp3) → miniaudio playback → Speaker
```

## Environment (this PC)

- Project: `C:\Users\bohen\jarvis\` — `.venv` + `jarvis.py` + `mic_check.py`.
- Deps installed in `.venv`: `faster-whisper sounddevice openwakeword
  edge-tts numpy miniaudio` (`uv pip install --python ./.venv/Scripts/python.exe …`).
- **Real input mic = Realtek Microphone Array, device id 5.** The Iriun
  webcam "microphones" read true zeros unless the Iriun app is feeding
  audio — never pick them as default. Voicemeeter virtual devices present
  too. `sounddevice.query_devices()` to enumerate; `--mic 5` to select.
- Output: default speakers via miniaudio (device auto).

## Hermes integration (the critical call)

```python
subprocess.run(["hermes", "chat", "-q", prompt, "-Q", "--continue", session],
               capture_output=True, text=True, timeout=120)
```

- `-q <text>` = one-shot query. `-Q` = quiet/programmatic (no banner/spinner).
- `--continue <name>` keeps a named session so Jarvis remembers context
  across utterances. Response header line starts `session_id:` — strip it.
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
  trailing silence (RMS dB below ~30); trim leading silence before STT.

## Deterministic testing (no human needed)

Validate STT/TTS without a live speaker: **generate known audio with
edge-tts, then transcribe it with whisper**. If the transcript matches the
prompt, the speech chain is proven; the only remaining variable is mic
pickup level. Example: `edge_tts.Communicate("Turn on the lights", …).save()`
→ `WhisperModel("base").transcribe(mp3)` → expect the same words.

## Pitfalls

- Splat-style argument passing: pass args unpacked, not as one list/tuple.
- MSYS path mangling: native Windows python wants `C:\...` paths, not
  `/c/...` — `/tmp/...` in a heredoc can silently land in `C:\tmp`.
- Wake-word loop prints `[waiting for 'jarvis'...]` — test with
  `--cli` (Enter-to-talk) first, then hands-free.
- `--once` for a single utterance; `--list-devices` to enumerate mics.

## Verification checklist

1. `mic_check.py 3` while speaking → peak > 0.02 (voice level, not ambient).
2. Known-audio round-trip: TTS prompt → whisper transcript matches.
3. `hermes chat -q "Say OK" -Q` returns text (no `session_id:` line leaks).
4. `speak("…")` plays through the speakers (miniaudio, mp3).
5. Full `jarvis.py --cli --mic 5 --once` → speak, hear reply.

See `references/voice-loop-build.md` for the session build transcript
with exact commands and error→fix pairs.