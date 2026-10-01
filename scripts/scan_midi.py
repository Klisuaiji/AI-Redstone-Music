#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MIDI health-check report: read this output before arranging and it settles "which tracks to keep,
which instrument to map them to, whether the pitch range overflows, how large the quantization error
is" all at once (this is step 2 of SKILL.md).

Usage:
    python3 scripts/scan_midi.py song.mid
    python3 scripts/scan_midi.py song.mid --json report.json

Contents: file header / tempo / duration / per-track list (name, channel, program, note count,
pitch range, octave distribution) / GM drum histogram / rhythm grid and quantization error /
part mapping suggestions.
Standard library only.
"""
import argparse, collections, json, math, os, sys

try:            # Windows console defaults to GBK: let non-GBK characters (⚠ etc.) degrade to ? instead of raising
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from midilib import read_midi, gm_drum_name

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# note block lower/upper pitch limits (F#1 - F#7), see references/instruments.md
NB_LO, NB_HI = 30, 102
# per-instrument base (the pitch at use-count 0) and reachable range = base..base+24
BASE = {"harp": 54, "bass": 30, "basedrum": 54, "snare": 54, "hat": 54, "bell": 78,
        "chime": 78, "flute": 66, "guitar": 42, "xylophone": 78, "iron_xylophone": 54,
        "cow_bell": 54, "didgeridoo": 30, "bit": 54, "banjo": 54, "pling": 54}


def nn(p):
    return "%s%d" % (NAMES[p % 12], p // 12 - 1)


def gcd_all(xs):
    g = 0
    for x in xs:
        g = math.gcd(g, int(abs(x)))
    return g


# common subdivisions (N equal parts per quarter note) -> name
SUBDIV = {1: "quarter", 2: "eighth", 3: "eighth triplet", 4: "sixteenth", 6: "sixteenth triplet",
          8: "thirty-second", 12: "thirty-second triplet", 16: "sixty-fourth",
          24: "sixty-fourth triplet", 32: "128th", 48: "128th triplet", 64: "256th",
          96: "256th triplet", 100: "1/100 quarter", 128: "512th", 192: "512th triplet",
          200: "1/200 quarter"}


def fit_grid(rel, division):
    """Can the offsets of all onsets relative to the first onset be explained by one musical grid?

    Returns (equal divisions per quarter note N, grid size in ticks, coverage), where N is the
    coarsest one with coverage >=98%.
    Computing gcd directly is ruined by "the grid is not an integer and export rounds it to an
    integer" (the deltas jump between 4/5 ticks and gcd degenerates to 1), so this enumerates the
    musically plausible subdivisions and allows a +/-1 tick rounding residue.
    """
    best = None
    for N in sorted(SUBDIV):        # N ascending = grid from coarse to fine; the first hit is the coarsest
        g = division / float(N)
        tol = max(1.0, g * 0.02)
        hit = 0
        for r in rel:
            k = round(r / g)
            if abs(r - k * g) <= tol:
                hit += 1
        cov = hit / float(len(rel))
        if cov >= 0.98:
            best = (N, g, cov)
            break
    return best


def main():
    ap = argparse.ArgumentParser(description="MIDI health-check report (take a look before arranging)")
    ap.add_argument("midi")
    ap.add_argument("--json", default=None, help="write the structured result to this JSON file")
    ap.add_argument("--speed", type=int, default=80, help="#speed used for the timeline conversion (default 80)")
    a = ap.parse_args()

    m = read_midi(a.midi)
    rep = {}
    print("=== %s ===" % a.midi)
    print("header: format=%d  MTrk count=%d (declared %d)  division=%d ticks/quarter note"
          % (m.fmt, len(m.tracks), m.declared_ntrks, m.division))
    print("tempo: %s" % " | ".join("%.3f BPM @tick %d" % (60e6 / u, t) for t, u in m.tempos))
    last = m.last_note_tick()
    print("duration: %.2f s (last note-on)  notes total: %d (note-on only)"
          % (m.sec_at(last), m.note_count))
    rep["file"] = a.midi
    rep["division"] = m.division
    rep["tempos"] = [{"tick": t, "bpm": 60e6 / u} for t, u in m.tempos]
    rep["duration_s"] = m.sec_at(last)
    rep["note_count"] = m.note_count

    # ---------- track list ----------
    print("\n--- track list ---")
    print(" %-3s %-30s %-6s %-8s %-6s %-18s %-24s %s"
          % ("#", "name", "chan", "program", "notes", "pitch range", "octaves (octave:count)", "start→end"))
    tracks_rep = []
    for t in m.tracks:
        if not t.notes:
            print(" %-3d %-30s %-6s %-8s %-6d %-18s %-24s %s"
                  % (t.index, t.name[:30], "-", "-", 0, "-", "-", "(empty track: tempo/markers)"))
            continue
        ps = t.pitches()
        octs = collections.Counter(n.pitch // 12 - 1 for n in t.notes)
        chans = ",".join(str(c) for c in sorted(t.channels))
        progs = ",".join(str(p) for _, p in t.programs) or "-"
        first, lastt = t.notes[0].tick, max(n.tick for n in t.notes)
        print(" %-3d %-30s %-6s %-8s %-6d %-18s %-24s %.2fs → %.2fs"
              % (t.index, t.name[:30], chans, progs, len(t.notes),
                 "%d..%d (%s..%s)" % (ps[0], ps[-1], nn(ps[0]), nn(ps[-1])),
                 " ".join("%d:%d" % (k, v) for k, v in sorted(octs.items())),
                 m.sec_at(first), m.sec_at(lastt)))
        tracks_rep.append({"index": t.index, "name": t.name, "notes": len(t.notes),
                           "channels": sorted(t.channels),
                           "programs": [p for _, p in t.programs],
                           "pitch_min": ps[0], "pitch_max": ps[-1],
                           "octaves": {str(k): v for k, v in sorted(octs.items())},
                           "is_drum": t.is_drum})
    rep["tracks"] = tracks_rep

    # ---------- drums ----------
    drum = collections.Counter()
    for t in m.tracks:
        for n in t.notes:
            if n.chan == 9:
                drum[n.pitch] += 1
    if drum:
        print("\n--- percussion (GM pitches) ---")
        line = []
        for p, c in sorted(drum.items()):
            line.append("%d %s ×%d" % (p, gm_drum_name(p), c))
        print(" " + " | ".join(line))
        print(" mapping suggestion: 36→basedrum 0.6 | 38/40→snare 0.5 | rest→hat 0.25 (drums: better too quiet than too loud)")
        rep["drums"] = {str(k): v for k, v in sorted(drum.items())}

    # ---------- rhythm grid ----------
    onsets = sorted(set(n.tick for t in m.tracks for n in t.notes))
    if len(onsets) > 1:
        tps = m.ticks_per_second(0)
        bpm = m.bpm_at(0)
        rel = [o - onsets[0] for o in onsets]
        g_rel = gcd_all(rel)
        fit = fit_grid(rel, m.division)
        sixteenth = m.division / 4.0
        on16 = sum(1 for o in onsets if abs(o / sixteenth - round(o / sixteenth)) < 1e-6)
        per_game_tick = tps / 20.0
        print("\n--- rhythm grid ---")
        print(" onsets (deduplicated): %d" % len(onsets))
        if fit:
            N, g, cov = fit
            name = SUBDIV.get(N, "1/%d note" % N)
            std = N in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 192)
            print(" best-fit grid: 1/%d quarter note (%s) = %.3f MIDI tick = %.2f ms, covering %.1f%% of onsets%s"
                  % (N, name, g, g / tps * 1000.0, cov * 100.0,
                     "" if std else " ← non-standard subdivision, most likely humanized/quantized output of a transcription tool"))
        else:
            print(" no regular grid with coverage >=98% found (gcd(onset deltas)=%d tick, so the playing is quite free)" % g_rel)
        print(" 16th-note grid: %.0f tick, onsets landing exactly on it: %.0f%%"
              % (sixteenth, 100.0 * on16 / len(onsets)))
        print(" timeline: 1 game tick = %.1f MIDI tick; at %.3f BPM one 16th note = %.3f game tick"
              % (per_game_tick, bpm, sixteenth / per_game_tick))
        err = per_game_tick / 2.0 / tps * 1000.0
        print(" max error of quantizing to 20 tps: %.1f ms (half a game tick, the physical floor, cannot be improved)" % err)
        print(" recommended form: time_unit=nbs_s_units + speed=%d (t is the game tick), "
              "t = round(seconds × 20) = round(MIDI tick × 20 / %.1f)" % (a.speed, tps))
        rep["grid"] = {"onsets": len(onsets), "gcd_delta": g_rel,
                       "best_grid": None if not fit else {"subdiv": fit[0], "ticks": fit[1], "coverage": fit[2]},
                       "on_16th_ratio": on16 / len(onsets),
                       "midi_ticks_per_game_tick": per_game_tick,
                       "max_quantize_error_ms": err}

    # ---------- part suggestions ----------
    print("\n--- part mapping suggestions (generate the details with midi_to_song.py) ---")
    for t in m.tracks:
        if not t.notes:
            continue
        ps = [n.pitch for n in t.notes]
        low = t.name.lower()
        if t.is_drum:
            print(" %d %-28s → drums (basedrum/snare/hat)" % (t.index, t.name[:28]))
            continue
        if "bass" in low or "\u8d1d" in low:      # "\u8d1d" = Chinese "bass" track-name alias (escape keeps the source ASCII)
            under = sum(1 for p in ps if p < NB_LO)
            extra = "; %d notes below F#1 (MIDI 30), must be raised an octave" % under if under else ""
            print(" %d %-28s → bass (vol 1.0)%s" % (t.index, t.name[:28], extra))
            continue
        hi = [p for p in ps if p >= 72]
        lo = [p for p in ps if p < 72]
        cand = [i for i, b in BASE.items() if b <= min(ps) and max(ps) <= b + 24 and i in
                ("flute", "pling", "bit", "harp", "bell", "chime")]
        print(" %d %-28s → split lead/chords: %d notes >=72, %d notes <72"
              % (t.index, t.name[:28], len(hi), len(lo)))
        if cand:
            print("    pitch range %d..%d fits a single instrument: %s" % (min(ps), max(ps), ", ".join(cand)))
        else:
            print("    pitch range %d..%d does not fit one instrument (each instrument spans only 25 semitones); "
                  "split it by register or fold octaves" % (min(ps), max(ps)))

    # ---------- verdict (one-line conclusion + next-step commands) ----------
    print("\n--- verdict ---")
    melodic = [t for t in m.tracks if t.notes and not t.is_drum and "bass" not in t.name.lower()
               and "\u8d1d" not in t.name.lower()]      # "\u8d1d" = Chinese "bass" track-name alias
    has_bass = any(t.notes and ("bass" in t.name.lower() or "\u8d1d" in t.name.lower()) for t in m.tracks)
    has_drum = any(t.notes and t.is_drum for t in m.tracks)
    voices = []
    if melodic:
        voices.append("melody %d" % len(melodic))
    if has_bass:
        voices.append("bass 1")
    if has_drum:
        voices.append("drums 1")
    # actual note tick count after quantization (t = round(seconds × 20))
    ticks = set()
    for t in m.tracks:
        for n in t.notes:
            ticks.add(int(round(m.sec_at(n.tick) * 20.0)))
    print(" parts: %s (%d non-empty tracks) → after quantizing to 20 tps: %d note ticks"
          % (", ".join(voices) or "none", sum(1 for t in m.tracks if t.notes), len(ticks)))
    if melodic:
        ps = [n.pitch for t in melodic for n in t.notes]
        mel_cands = ("flute", "pling", "bit", "harp", "bell", "chime")

        def best(v, cands):
            """Pick the instrument that needs the fewest octave folds; returns (instrument, notes to fold)."""
            if not v:
                return None, 0
            bi, bn = None, None
            for i in cands:
                lo, hi = BASE[i], BASE[i] + 24
                n = sum(1 for p in v if not (lo <= p <= hi))
                if bn is None or n < bn:
                    bi, bn = i, n
            return bi, bn

        i_all, n_all = best(ps, mel_cands)
        if max(ps) - min(ps) <= 24 and n_all == 0:
            print(" lead pitch range %d..%d (%d semitones) fits a single instrument: %s" % (min(ps), max(ps), max(ps) - min(ps), i_all))
        else:
            hi = [p for p in ps if p >= 72]
            lo = [p for p in ps if p < 72]
            ih, nh = best(hi, mel_cands)
            il, nl = best(lo, ("guitar", "harp", "banjo", "pling", "flute"))
            print(" lead pitch range %d..%d spans %d semitones and does not fit a single instrument (each spans only 25 semitones)" % (min(ps), max(ps), max(ps) - min(ps)))
            print("   best single-instrument coverage: %s (%d/%d notes out of range, need octave folding)" % (i_all, n_all, len(ps)))
            print("   splitting at 72 works better: >=72 with %s (%d/%d out of range), <72 with %s (%d/%d out of range)"
                  % (ih, nh, len(hi), il, nl, len(lo)))
    low = [(t.name, n.pitch) for t in m.tracks for n in t.notes if n.pitch < NB_LO]
    if low:
        print(" ⚠ %d notes below the note block lower limit F#1 (MIDI 30); they must be raised an octave (the pitch relations stay the same afterwards)" % len(low))
    if onsets and len(ticks) < len(onsets):
        print(" ⚠ quantized tick count (%d) < onset count (%d): some notes collapsed onto the same tick "
              "(the 20 tps grid is too coarse; consider /tick rate 40/80 to refine it)" % (len(ticks), len(onsets)))
    print(" next step: python3 scripts/midi_to_song.py %s -o song.json --name <song name> --song-id <unused id>"
          % os.path.basename(a.midi))
    print("         python3 scripts/make_datapack.py song.json -o out/<song name> --mc-version <version>   # or generate.py + validate_pack.py")

    if a.json:
        rep["verdict"] = {"voices": voices, "quantized_ticks": len(ticks)}
        rep["ticks_after_quantize"] = len(ticks)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print("\nstructured result → %s" % a.json)


if __name__ == "__main__":
    main()
