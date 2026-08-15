#!/usr/bin/env python3
"""Transcribe audio/video to timestamped text, then optionally seed a storyboard.

Input: any audio (wav/mp3/m4a/flac/ogg) or video (mp4/mov/mkv/…) file —
PyAV decodes it, so no external ffmpeg needed. Outputs JSON (segments + word
timestamps), SRT, VTT, and plain text; with --storyboard also emits a
panel-by-panel storyboard seeded from the spoken beats.

Engine: faster-whisper (local, CPU int8). Model is auto-cached to
~/.cache/huggingface/hub on first use; "base" is the default.
"""
import argparse
import json
import os
import sys


def fmt_srt(seconds: float) -> str:
    """SRT timestamp: HH:MM:SS,mmm"""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_vtt(seconds: float) -> str:
    """VTT timestamp: HH:MM:SS.mmm"""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def fmt_clock(seconds: float) -> str:
    """Human clock: H:MM:SS"""
    s = int(round(seconds))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}"


def write_srt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{fmt_srt(seg['start'])} --> {fmt_srt(seg['end'])}\n{seg['text']}\n\n")


def write_vtt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for seg in segments:
            f.write(f"{fmt_vtt(seg['start'])} --> {fmt_vtt(seg['end'])}\n{seg['text']}\n\n")


def write_txt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"[{fmt_clock(seg['start'])} - {fmt_clock(seg['end'])}] {seg['text']}\n")


def write_json(payload, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_storyboard(segments, title, path, language):
    """Seed a storyboard: each spoken beat becomes a panel (visuals left blank)."""
    title = title or os.path.splitext(os.path.basename(path))[0]
    lines = [
        f"# {title} — Storyboard (audio-seeded)",
        "",
        f"Language: {language}   |   Beats: {len(segments)}   |   Source: audio transcription",
        "",
        "## Global style (fill in / lock for consistency)",
        "- Subject / character(s):",
        "- Lighting (source, direction, quality, color temp):",
        "- Color grade / palette:",
        "- Mood / tone:",
        "- Style (photorealistic / cinematic / animation):",
        "",
        "## Panels",
        "",
    ]
    for i, seg in enumerate(segments, 1):
        dur = seg["end"] - seg["start"]
        lines += [
            f"### Shot {i}",
            f"- Size:        (EWS / WS / FS / MS / MCU / CU / ECU / OTS / POV)",
            f"- Angle:       (eye-level / high / low / Dutch / overhead)",
            f"- Movement:    (static / pan / tilt / dolly / zoom / tracking / orbit / handheld)",
            f"- Action:      (describe the visual — what is on screen)",
            f"- Dialogue/VO: {seg['text']}",
            f"- On-screen text:",
            f"- Audio/SFX/music:",
            f"- Duration:    {dur:.1f}s",
            f"- Transition:  cut",
            f"- Timestamp:   {fmt_clock(seg['start'])} -> {fmt_clock(seg['end'])}",
            f"- Visual / AI prompt:",
            "",
        ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description="Transcribe audio/video to timestamped text (and optionally a storyboard).")
    ap.add_argument("input", help="audio or video file to transcribe")
    ap.add_argument("-o", "--output", help="output base path (default: input path minus extension)")
    ap.add_argument("--model", default="base", help="whisper model: tiny/base/small/medium/large-v3 (default: base)")
    ap.add_argument("--language", default=None, help="force language code (e.g. en, fr); default auto-detect")
    ap.add_argument("--vad", action="store_true", help="enable Silero VAD to filter silence")
    ap.add_argument("--storyboard", action="store_true", help="also emit a storyboard markdown seeded from the transcript")
    ap.add_argument("--title", default=None, help="storyboard title (default: output base name)")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"ERROR: input not found: {args.input}")

    from faster_whisper import WhisperModel

    print(f"Loading model '{args.model}' (cpu, int8)…")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    print(f"Transcribing: {args.input}")
    segments_iter, info = model.transcribe(
        args.input,
        word_timestamps=True,
        language=args.language,
        vad_filter=args.vad,
        beam_size=5,
    )
    segments = []
    for s in segments_iter:
        words = [{"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word} for w in (s.words or [])]
        segments.append({"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(), "words": words})

    base = args.output or os.path.splitext(args.input)[0]
    txt = " ".join(seg["text"] for seg in segments)

    payload = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "model": args.model,
        "segments": segments,
        "text": txt,
    }

    write_json(payload, base + ".json")
    write_srt(segments, base + ".srt")
    write_vtt(segments, base + ".vtt")
    write_txt(segments, base + ".txt")
    print(f"✓ {len(segments)} segments | language={info.language} | {info.duration:.1f}s audio")
    print(f"  .json (full + word timestamps), .srt, .vtt, .txt -> {base}.*")

    if args.storyboard:
        sb_path = base + ".storyboard.md"
        write_storyboard(segments, args.title or os.path.basename(base), sb_path, info.language)
        print(f"  .storyboard.md -> {sb_path}")


if __name__ == "__main__":
    main()
