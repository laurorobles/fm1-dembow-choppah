#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Convert and optimize raw Dembow loops (WAV/MP3/AIFF/FLAC/OGG) for CHOPPAH FM-1.

Steps per file:
1. Decode to 44.1 kHz mono float via ffmpeg (handles MP3 encoder delay, stereo->mono, 24-bit, etc.).
2. Trim leading silence (> -50 dBFS) so beat 1 starts on sample 0.
3. Snap to whole bars (1 or 2 bars) and compute BPM, or use explicit --bpm / --bars.
4. Level to -16 dBFS RMS with look-ahead limiter (using prep_breaks.level).
5. Resample to 22,050 Hz (or highest rate <= 22,050 Hz that fits CH_PCM_MAX = 106,496 samples).
6. Write optimized 16-bit mono WAV into breaks/dembow/ and generate breaks/dembow_breaks.txt.
"""
import argparse
import math
import re
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prep_breaks as pb

AUDIO_EXTS = {".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a"}


def decode_with_ffmpeg(src: Path) -> tuple[list[float], int]:
    """Decode any audio file to 44.1 kHz mono float samples via ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp = Path(tf.name)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "44100", "-c:a", "pcm_f32le", str(tmp)],
            check=True,
        )
        return pb.read_wav(tmp)
    finally:
        if tmp.exists():
            tmp.unlink()


def trim_leading_silence(x: list[float], threshold: float = 0.00316) -> tuple[list[float], int]:
    """Remove leading samples below threshold (-50 dBFS) so transient 1 starts cleanly."""
    first = next((i for i, v in enumerate(x) if abs(v) > threshold), 0)
    return x[first:], first


def trim_trailing_silence(x: list[float], threshold: float = 0.001) -> tuple[list[float], int]:
    """Remove trailing silence below -60 dBFS."""
    last = len(x) - 1 - next((i for i, v in enumerate(reversed(x)) if abs(v) > threshold), 0)
    return x[: last + 1], len(x) - 1 - last


def guess_bpm_and_bars(dur_s: float, filename: str) -> tuple[float, int]:
    """Infer BPM and bar count from filename hints or duration (assuming 80..135 BPM)."""
    m = re.search(r"(?:bpm[\s_-]*(\d+(?:\.\d+)?)|^(\d{2,3})_)", filename, re.IGNORECASE)
    hint_bpm = float(m.group(1) or m.group(2)) if m else None
    if hint_bpm and 75.0 <= hint_bpm <= 150.0:
        bars = max(1, round(dur_s * hint_bpm / 240.0))
        return hint_bpm, bars

    # Otherwise pick bar count (1, 2, 4) that yields the most natural dembow BPM (88..130)
    candidates = []
    for b in (1, 2, 4):
        bpm = 240.0 * b / dur_s
        if 85.0 <= bpm <= 135.0:
            # Prefer ~95-105 BPM center
            candidates.append((abs(bpm - 100.0), b, bpm))
    if candidates:
        candidates.sort()
        _, b, bpm = candidates[0]
        return round(bpm, 2), b
    return round(240.0 / dur_s, 2), 1


def clean_name(stem: str) -> str:
    """Short uppercase name (max 11 chars) for the FM-1 screen."""
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", stem).strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s[:11] if s else "DEMBOW"


def write_wav_16(path: Path, samples: list[float], rate: int) -> None:
    """Write mono 16-bit PCM WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = struct.pack(f"<{len(samples)}h", *(max(-32768, min(32767, int(round(v * 32767.0)))) for v in samples))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def process_file(src: Path, out_dir: Path, target_rate: int = 22050, max_bars: int = 2,
                 target_db: float = -16.0) -> dict:
    """Decode, trim, level, fit to CH_PCM_MAX, and write optimized WAV."""
    x, rate = decode_with_ffmpeg(src)
    x, lead_n = trim_leading_silence(x)
    x, tail_n = trim_trailing_silence(x)
    dur_s = len(x) / rate

    bpm, total_bars = guess_bpm_and_bars(dur_s, src.stem)
    use_bars = min(max_bars, total_bars)
    bar_samples = rate * 240.0 / bpm
    want_samples = int(round(bar_samples * use_bars))
    if want_samples <= len(x):
        x = x[:want_samples]
    else:
        # Loop has slightly fewer samples than exact bar math: adjust bpm to actual trimmed length
        bpm = round(240.0 * use_bars / (len(x) / rate), 2)

    # Apply tiny 2ms fade-out at the very end to avoid click at loop wrap
    fade = min(len(x), int(rate * 0.002))
    for i in range(fade):
        x[len(x) - 1 - i] *= i / fade

    # Level to -16 dBFS with look-ahead limiter
    x, gain_db, lim_db = pb.level(x, rate, target_db)

    # Choose rate: default 22050, or lower if > CH_PCM_MAX (106,496 samples)
    est_len = int(len(x) * target_rate / rate)
    chosen_rate = target_rate
    if est_len > pb.BANK_MAX_LEN:
        # Either drop to 1 bar at 22050 Hz, or reduce rate; reducing rate preserves 2 bars!
        chosen_rate = int(pb.BANK_MAX_LEN * rate / len(x)) - 50
        chosen_rate = max(16000, chosen_rate)

    x_res = pb.resample(x, rate, chosen_rate)
    if len(x_res) > pb.BANK_MAX_LEN:
        x_res = x_res[:pb.BANK_MAX_LEN]

    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", src.stem).strip("_").lower()
    out_wav = out_dir / f"{safe_stem}.wav"
    write_wav_16(out_wav, x_res, chosen_rate)

    return {
        "src": src.name,
        "out": out_wav,
        "rel": f"dembow/{out_wav.name}",
        "bpm": bpm,
        "bars": use_bars,
        "of_bars": total_bars,
        "rate": chosen_rate,
        "samples": len(x_res),
        "lead_ms": round(lead_n / rate * 1000.0, 1),
        "gain_db": round(gain_db, 1),
        "lim_db": round(lim_db, 1),
        "name": clean_name(src.stem),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_dir", type=Path, help="Folder containing raw dembow loops")
    ap.add_argument("--out-dir", type=Path, default=Path("breaks/dembow"), help="Output folder for optimized WAVs")
    ap.add_argument("--catalog", type=Path, default=Path("breaks/dembow_breaks.txt"), help="Output breaks.txt catalog")
    ap.add_argument("--rate", type=int, default=22050, help="Target sample rate (default 22050)")
    ap.add_argument("--max-bars", type=int, default=2, help="Max bars per break (default 2)")
    args = ap.parse_args()

    files = sorted(p for p in args.input_dir.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS)
    if not files:
        raise SystemExit(f"No audio files found in {args.input_dir}")

    results = []
    for f in files:
        res = process_file(f, args.out_dir, target_rate=args.rate, max_bars=args.max_bars)
        results.append(res)
        print(
            f"{res['src']:32s} -> {res['out'].name:30s} | {res['bpm']:6.2f} BPM | "
            f"{res['bars']}b | {res['rate']} Hz | {res['samples']:6d} smp | "
            f"trim {res['lead_ms']:4.1f}ms | gain {res['gain_db']:+5.1f}dB"
        )

    lines = [
        "# CHOPPAH DEMBOW custom break bank (generated by tools/dembow_convert.py)",
        "# in  file                                        bpm     bars  of  name",
    ]
    for r in results:
        lines.append(f"*   {r['rel']:<43s} {r['bpm']:<7.2f} {r['bars']:<5d} {r['of_bars']:<3d} {r['name']}")
    args.catalog.parent.mkdir(parents=True, exist_ok=True)
    args.catalog.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote catalog: {args.catalog}")


if __name__ == "__main__":
    main()
