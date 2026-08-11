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

## VAD calibration (real measurements, 2026-08-09)

`--levels` meter at the user's normal sitting distance (~2 m, mic 5):

- Speech chunks: 0.0057–0.037 RMS (typical 0.006–0.009 for quiet talk)
- Noise/silence: 0.0000–0.0043 RMS (peaks ~0.0045)

The first attempt used `SILENCE_DB = 30.0` (a dB cutoff) → every audio
frame read as "silence" (`rms_db < 30` is always true for float audio) and
the recorder broke out after ~1 s regardless of speech. Fix: linear RMS
`SILENCE_RMS = 0.004` + `SPEECH_CONFIRM_CHUNKS = 2`. Dry-run against the
measured samples: 9/9 speech chunks above threshold, noise would need two
consecutive super-threshold chunks to trigger (didn't happen).

Lesson: the gap between quiet speech and noise was only ~0.0015 RMS —
software thresholding is the wrong tool at that margin. Recommended the
hardware fix: +20 dB mic boost (mmsys.cpl → Recording → Realtek Array →
Properties → Levels). Also added to jarvis.py: `--levels [SECONDS]` live
RMS meter that mirrors the VAD's debounce logic.

Also fixed: `run.cmd` launcher failed with `'M' is not recognized` — the
file had a UTF-8 em-dash (0xE2 0x80 0x94) in the REM comment and LF line
endings. Rewritten ASCII-only + CRLF; verified via
`powershell -NoProfile -Command "& .\run.cmd --levels 2 --mic 5"`.

## Noise reduction (measured 2026-08-09)

Quiet-room ambient on the Realtek Array: **RMS 0.00017, −75 dB**, flat,
no mains hum, no dominant tone (peak band ~152 Hz at −99 dB). Per-chunk
max 0.00027 → the 0.0043 "noise" seen in the earlier `--levels` run was
user movement/keyboard transients, not steady noise. Conclusion: the loop
was signal-limited (voice 0.008 RMS at sitting distance), not noise-limited.

DSP validation rig (fix the rig before trusting regressions — a stereo
downmix bug made noisereduce look harmful first pass):

| Pipeline | Residual noise | Whisper char-accuracy |
|---|---|---|
| raw | 0.00408 | 67.2% |
| noisereduce only (prop_decrease=0.9) | 0.00120 (−70%) | 98.3% |
| high-pass 80 Hz butter(4) | 0.00618 | — |
| high-pass + noisereduce | 0.00215 | 20.7% |

- Sampling: `dec.nchannels == 2` for edge-tts mp3 → `np.frombuffer`(
  `dec.samples`) is interleaved L/R; downmix `buf[0::2]` or average
  channels before `resample_poly` to 16 kHz.
- Wider-band white-ish noise (SNR ~10 dB) showed NO difference between
  raw/hp/den — whisper was already fine there; gating pays off in the
  transient/spike regime (real room).
- `vad_filter=True` added to transcribe; `--levels` meter mirrors the
  debounce logic (2-chunk confirm) so what you see is what the VAD does.

Production decision: adaptive gating in jarvis.py — capture a 2 s noise
profile at startup (discarding the first ~0.5 s buffer — MME first-read
garbage caused a NaN crash before the warmup was added); skip gating when
the profile RMS < 0.0005 to avoid artifacts in an already-quiet room.

## Environment hygiene discovered

- Hermes-session env exports PYTHONPATH that puts
  `AppData\Local\hermes\hermes-agent` + its `venv\Lib\site-packages` AHEAD
  of the project venv → `import numpy` resolves from the wrong venv.
  Fix: `PYTHONPATH= ./.venv/Scripts/python.exe …` (or `set PYTHONPATH=`
  in run.cmd).
- OS default input verified via Core Audio GetDefaultAudioEndpoint:
  Realtek Array for both CAPTURE roles — `--mic 5` is redundant but safe;
  drift risk if Iriun app ever claims the default role.

## Open items / next steps

- ~~Live speaker test of the full loop~~ DONE (2026-08-09): "Time, time."
  → 18 s reasoning → correct Ghana-time answer. Session continuity
  verified across two utterances.
- Wake-word sensitivity tuning (current threshold 0.5).
- Voicemeeter capture test (could give better gain than Realtek Array).
- Consider `tiny` whisper for latency if base feels slow.
- After +20 dB mic boost: re-run `--levels` to confirm the speech/noise gap
  widened before relying on wake-word hands-free mode.