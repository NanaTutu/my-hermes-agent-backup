---
name: audio-transcription
description: Use when transcribing audio or video to timestamped text.
---

# Audio Transcription → Storyboard

Transcribe an audio/video file to timestamped text, then feed it into the
storyboard workflow. Local and offline (faster-whisper on CPU), no API keys.

## The tool

`C:\Users\bohen\Documents\Hermes\audio2storyboard\transcribe.py` (venv `.venv`).

Run:
```bash
cd /c/Users/bohen/Documents/Hermes/audio2storyboard
.venv/Scripts/python.exe transcribe.py <input> [--storyboard] [--title "Name"]
```

- **Input: any audio or video** (mp3, wav, m4a, aac, flac, ogg, mp4, mov, mkv…).
  PyAV (a faster-whisper dependency) decodes it — mp4/video audio tracks are
  extracted automatically, so no external ffmpeg is needed.
- **Outputs** `<base>.json` (segments + word-level timestamps), `.srt`, `.vtt`,
  `.txt`, and with `--storyboard` also a `<base>.storyboard.md`.

## Flags

- `--model` tiny/base/small/medium/large-v3 (default `base`). `base` is already
  cached; `small`/`medium` are more accurate but ~0.5–1.5 GB, downloaded once.
- `--language` force a code (en, fr…) — default auto-detect.
- `--vad` enable Silero VAD to filter silence out.
- `--storyboard` + `--title` emit the storyboard seed.

## How it feeds the storyboard workflow

1. Transcribe: `.venv/Scripts/python.exe transcribe.py sermon.mp4 --storyboard --title "Sermon"`
2. The `.storyboard.md` has one panel per spoken beat: `Dialogue/VO` filled from
   the transcript, `Duration` + `Timestamp` from the audio; the visual fields
   (Size, Angle, Movement, Action, Visual/AI prompt) are left blank to fill in.
3. Complete the visuals using the `storyboard-creation` skill (shot vocab +
   AI-prompt formula), then hand off to `capcut-automation`: each shot becomes a
   timeline element, and the `.srt` feeds the vectcut MCP `add_subtitle` tool
   (or CapCut's direct subtitle import).

## Details & pitfalls

- Engine: `faster-whisper` 1.2.1 — `WhisperModel(model, device="cpu",
  compute_type="int8")`, same as the Jarvis voice-loop. The `base` model is
  cached in `~/.cache/huggingface/hub`.
- Word timestamps need `word_timestamps=True` (already set in the script).
- First run of a NEW `--model` downloads it over the network (hotspot!) — stay
  on `base` unless accuracy demands otherwise.
- `base` handles clear English well; for accented/noisy audio or precise word
  timing, step up to `small` or `medium`.
- Model load ~1–2 s; transcription is CPU-bound (base ≈ real-time or faster on
  this box — no CUDA, Intel UHD only).
- The `.srt` output imports directly into CapCut (subtitles) and into the vectcut
  MCP `add_subtitle` tool.
