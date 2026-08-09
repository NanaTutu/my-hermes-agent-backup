# Voice Loop Build Transcript (Aug 2026)

Session-by-session record of building `jarvis.py` at `C:\Users\bohen\jarvis\`.
Read this when debugging or extending the loop — every line below is a real
error→fix pair from the build.

## Setup

```bash
mkdir C:\Users\bohen\jarvis && cd C:\Users\bohen\jarvis
uv venv .venv --python 3.11
uv pip install --python ./.venv/Scripts/python.exe faster-whisper sounddevice openwakeword edge-tts numpy miniaudio
```

First `WhisperModel("base")` call downloads the model (~50-100 MB) — takes
about a minute, prints nothing until it finishes. Warm it before a live demo.

## Mic selection

`sounddevice.query_devices()` on this PC shows ~30 devices: Realtek
Microphone Array (physical), several "Microphone (Iriun Webcam)" entries,
Voicemeeter virtual buses. **Only the Realtek Array (id 5) captures real
sound**; the Iriun entries sit at peak 0.0000 unless the Iriun app runs.
Voicemeeter inputs need the Voicemeeter app routing audio.

`mic_check.py 3` (record 3 s, print RMS/peak) is the mic sanity probe.
Speaking produces peak > 0.02; ambient-only reads ~0.001-0.008.

## Error → fix log

| Error | Cause | Fix |
|---|---|---|
| `unsupported arg type <class 'list'>` | `encode_osc(addr, args)` — args is a list; encoder wants unpacked | call `encode_osc(addr, *args)` |
| `NameError: name 'address' is not defined` | returned a variable that was renamed (`addr`) | return the actual local |
| `NameError: name 'WingClient' is not defined` | class renamed to `WingOSC`, call sites stale | grep every call site after any rename |
| `Media.SoundPlayer ... not a valid wave file` | PowerShell SoundPlayer only plays WAV; edge-tts emits MP3 | switch playback to miniaudio |
| `module 'miniaudio' has no attribute 'play_file'` | `play_file` removed in miniaudio ≥1.71 | use `PlaybackDevice` + `dev.start(miniaudio.stream_file(...))` |
| `PlaybackDevice.start() missing 1 required positional argument: 'callback_generator'` | `start()` takes the streaming generator | pass `dev.start(miniaudio.stream_file(str(mp3)))` |
| transcript of a sine wave = `''` | expected — no speech in the file | not a bug; proves chain runs |
| FileNotFoundError on `/tmp/CHURCH_edited.sav` | Windows python resolves `/tmp/` to `C:\tmp\`, not bash `/tmp` | always pass native `C:\...` paths to Windows python |

## Deterministic test trick

No human speaker needed to verify STT: generate audio with edge-tts
(`"Hello Jarvis, this is a pipeline test. Turn on the lights."`) then
transcribe with faster-whisper. Got back the same words (lowercased,
punctuation dropped) — speech chain proven in isolation. Then only the mic
pickup needs a human.

## Latency budget (free model)

`hermes chat -q -Q` one-shot: **18.8 s** wall time measured (mostly model
inference). Plus whisper (~1-3 s base int8) plus TTS (~1 s). Total Jarvis
round-trip ≈ 22 s on the free model. Mitigations: faster model via
`-m`, or smaller whisper (`tiny`).

## Open items / next steps

- Live speaker test of the full loop (`--cli --mic 5 --once`) pending.
- Wake-word sensitivity tuning (current threshold 0.5).
- Voicemeeter capture test (could give better gain than Realtek Array).
- Consider `tiny` whisper for latency if base feels slow.