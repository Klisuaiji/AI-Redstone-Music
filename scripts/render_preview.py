#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""song.json → WAV preview (listen to the arrangement once without opening Minecraft).

Works out each note's **game tick** from the timeline rules in song.json (exactly the same
conversion as generate.py), then renders it to WAV with simple synthetic timbres: decaying sines
with harmonics for the melody, a frequency sweep / noise for the drums.
The pitch is the MIDI pitch itself (the note block design guarantees
"instrument base + use-count = original pitch"), so the perceived pitch relations match the game,
only the timbre differs.

Usage:
    python3 scripts/render_preview.py song.json -o preview.wav
    python3 scripts/render_preview.py song.json -o piano.wav --lead-inst pling   # try another timbre
    python3 scripts/render_preview.py song.json -o head.wav --slice 0 30         # first 30 seconds only

Standard library only (wave / array / math).
"""
import argparse, array, json, math, os, sys, wave

try:            # Windows console defaults to GBK: let non-GBK characters (⚠ etc.) degrade to ? instead of raising
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# per-instrument harmonic mix (1st/2nd/3rd harmonic) and decay time constant (seconds)
TIMBRE = {
    "harp":   ((1.0, 0.32, 0.12), 0.55), "pling":  ((1.0, 0.45, 0.22), 0.45),
    "bit":    ((1.0, 0.55, 0.35), 0.30), "banjo":  ((1.0, 0.40, 0.25), 0.35),
    "guitar": ((1.0, 0.38, 0.16), 0.50), "flute":  ((1.0, 0.12, 0.04), 0.45),
    "bass":   ((1.0, 0.28, 0.10), 0.50), "didgeridoo": ((1.0, 0.45, 0.25), 0.45),
    "bell":   ((1.0, 0.50, 0.30), 0.90), "chime":  ((1.0, 0.50, 0.30), 0.90),
    "xylophone": ((1.0, 0.20, 0.06), 0.30), "iron_xylophone": ((1.0, 0.25, 0.10), 0.45),
    "cow_bell": ((1.0, 0.45, 0.28), 0.35),
}
BASE = {"harp": 54, "bass": 30, "basedrum": 54, "snare": 54, "hat": 54, "bell": 78,
        "chime": 78, "flute": 66, "guitar": 42, "xylophone": 78, "iron_xylophone": 54,
        "cow_bell": 54, "didgeridoo": 30, "bit": 54, "banjo": 54, "pling": 54}


def midi_freq(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))


def main():
    ap = argparse.ArgumentParser(description="song.json → WAV preview")
    ap.add_argument("song")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--rate", type=int, default=22050, help="sample rate (default 22050, good enough to listen)")
    ap.add_argument("--slice", nargs=2, type=float, default=None, metavar=("START", "END"),
                    help="render only this time range (seconds)")
    ap.add_argument("--tail", type=float, default=1.0, help="seconds of silence at the end")
    ap.add_argument("--swap", action="append", default=[], metavar="FROM=TO",
                    help="swap an instrument for another timbre in the preview; repeatable (e.g. harp=pling)")
    ap.add_argument("--gain", type=float, default=0.9, help="overall gain (default 0.9; normalized to this peak)")
    a = ap.parse_args()

    song = json.load(open(a.song, encoding="utf-8"))
    meta = song.get("meta", {})
    unit = meta.get("time_unit", "nbs_ticks")
    speed = meta.get("speed", 2)
    tps = meta.get("tempo_tps", 10)
    scale = {"nbs_ticks": 20.0 / tps * speed, "game_ticks": float(speed)}.get(unit, 1.0)
    swap = {}
    for kv in a.swap:
        if "=" in kv:
            k, v = kv.split("=", 1)
            swap[k.strip()] = v.strip()

    # collect notes: t → game tick (same conversion as generate.py: T = round(t*scale), fires at game tick 80T/speed)
    events = []
    for tr in song.get("tracks", []):
        if tr.get("include", True) is False:
            continue
        dflt = tr.get("instrument_default", "harp")
        for n in tr["notes"]:
            inst = swap.get(n.get("inst", dflt), n.get("inst", dflt))
            T = int(round(n["t"] * scale))
            tick = 80.0 * T / speed
            events.append((tick / 20.0, inst, n["midi"], float(n.get("vol", 1.0))))
    if not events:
        sys.exit("no notes in song.json")
    events.sort()
    total = events[-1][0] + a.tail
    t0, t1 = (a.slice[0], a.slice[1]) if a.slice else (0.0, total)
    t1 = min(t1, total)

    rate = a.rate
    n_samples = int((t1 - t0) * rate) + 1
    buf = [0.0] * n_samples
    used = 0
    for start, inst, midi, vol in events:
        if start < t0 - 1.0 or start > t1:
            continue
        used += 1
        i0 = int((start - t0) * rate)
        if i0 < 0:
            i0 = 0
        if inst in ("basedrum", "snare", "hat"):
            dur = {"basedrum": 0.16, "snare": 0.12, "hat": 0.05}[inst]
        else:
            dur = TIMBRE.get(inst, ((1.0, 0.3, 0.1), 0.5))[1] * 2.2
        ns = int(dur * rate)
        if i0 >= n_samples:
            continue
        ns = min(ns, n_samples - i0)
        if inst == "basedrum":                       # 120 → 45 Hz frequency sweep
            ph = 0.0
            for i in range(ns):
                f = 45.0 + 75.0 * math.exp(-i / (0.03 * rate))
                ph += 2 * math.pi * f / rate
                buf[i0 + i] += vol * 1.2 * math.sin(ph) * math.exp(-i / (0.045 * rate))
        elif inst in ("snare", "hat"):               # noise + a little tone
            dec = (0.030 if inst == "snare" else 0.012) * rate
            seed = 12345
            for i in range(ns):
                seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
                noise = (seed / 0x3FFFFFFF) - 1.0
                env = math.exp(-i / dec)
                v = noise * env
                if inst == "snare":
                    v = v * 0.9 + 0.25 * math.sin(2 * math.pi * 190 * i / rate) * env
                buf[i0 + i] += vol * (1.6 if inst == "hat" else 1.3) * v
        else:
            h, tau = TIMBRE.get(inst, ((1.0, 0.3, 0.1), 0.5))
            w0 = 2 * math.pi * midi_freq(midi) / rate
            dec = tau * rate
            atk = max(1, int(0.004 * rate))
            for i in range(ns):
                e = math.exp(-i / dec)
                if i < atk:
                    e *= i / float(atk)
                ph = w0 * i
                s = h[0] * math.sin(ph) + h[1] * math.sin(2 * ph) + h[2] * math.sin(3 * ph)
                buf[i0 + i] += vol * 0.32 * s * e

    peak = max(abs(x) for x in buf) or 1.0
    k = a.gain / peak
    pcm = array.array("h", bytes(2 * n_samples))
    for i in range(n_samples):
        pcm[i] = int(max(-32767, min(32767, buf[i] * k * 32767)))

    with wave.open(a.out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())

    rms = math.sqrt(sum((x / 32767.0) ** 2 for x in pcm[::7]) / max(1, len(pcm[::7])))
    print("WAV → %s" % a.out)
    print("  %.2f s / %d Hz / mono 16bit / rendered %d notes (of %d)"
          % (t1 - t0, rate, used, len(events)))
    print("  peak %.2f (normalized to %.2f) / RMS %.4f / file %.2f MB"
          % (peak * k, a.gain, rms, os.path.getsize(a.out) / 1e6))
    if a.slice:
        print("  ⚠ rendered only the slice %.1fs–%.1fs; drop --slice for the full preview" % (t0, t1))


if __name__ == "__main__":
    main()
