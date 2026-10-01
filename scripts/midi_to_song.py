#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MIDI → song.json (automatic arranging + arrangement decision report).

Turns the "human judgement" parts of steps 3 and 4 of SKILL.md into reproducible rules:
track classification → instrument mapping → volume table → timeline quantization → pitch-range
folding → dedupe → write song.json (+ report).

By default the timeline follows the **verified convention**: `time_unit=nbs_s_units` + `speed=80`,
i.e. t in song.json is the game tick (host `#speed nbs_s 80`, tree window 80×t).
With a different `--speed`, the timeline is rescaled as t = round(game tick × S/80) and a
resolution-loss warning is printed.

Usage:
    python3 scripts/midi_to_song.py song.mid -o song.json --name m3 --song-id 9 \\
        --mc-version 26.2 --lead-split 72 --lead-inst flute --report arrangement.md

Afterwards:
    python3 scripts/generate.py song.json -o out/music/m3
    python3 scripts/validate_pack.py --pack out --namespace minecraft --song m3 --song-id 9 --speed 80
Standard library only (generate.py's instrument table is reused so the criteria match validation).
"""
import argparse, collections, json, os, re, sys

try:            # Windows console defaults to GBK: let non-GBK characters (⚠ etc.) degrade to ? instead of raising
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from midilib import read_midi, gm_drum_name
from generate import INSTRUMENTS, HEADS

# default mix volumes (section 6 of references/midi_notes.md, calibrated by ear)
DEFAULT_VOL = {"basedrum": 0.6, "snare": 0.5, "hat": 0.25, "bit": 0.5}
# Chinese track-name aliases are kept as \u escapes so the source stays pure ASCII (match behavior unchanged)
DRUM_KEYWORDS = ("drum", "perc", "beat", "\u9f13", "\u6253\u51fb")
BASS_KEYWORDS = ("bass", "\u8d1d\u65af", "\u8d1d\u53f8", "\u4f4e\u97f3")


def vol_of(inst, overrides):
    if inst in overrides:
        return overrides[inst]
    return DEFAULT_VOL.get(inst, 1.0)


def vtuple(v):
    return tuple(int(x) for x in str(v).split("."))


def sanitize(name):
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", name).strip("_").lower()
    return s or "song"


def main():
    ap = argparse.ArgumentParser(description="MIDI → song.json (automatic arranging)")
    ap.add_argument("midi")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--name", default=None, help="song name (used in the path; defaults to the file name)")
    ap.add_argument("--namespace", default="minecraft")
    ap.add_argument("--path", default=None, help="function path, defaults to music/<name>")
    ap.add_argument("--song-id", type=int, default=8)
    ap.add_argument("--mc-version", default="26.2")
    ap.add_argument("--speed", type=int, default=80, help="#speed nbs_s (default 80 = t is the game tick)")
    ap.add_argument("--tick-rate", type=int, default=20,
                    help="host tick rate: 20=vanilla (50ms grid); 80 refines the time grid to 12.5ms (needs MC 1.20.3+ and a manual /tick rate 80)")
    ap.add_argument("--style", choices=["lemon", "standalone"], default="standalone")
    ap.add_argument("--lead-split", type=int, default=72, help="pitches at or above this count as lead melody (default 72)")
    ap.add_argument("--lead-inst", default="auto",
                    help="lead instrument; auto (default) = use a single instrument if the whole track fits, otherwise split at --lead-split")
    ap.add_argument("--chord-inst", default="guitar")
    ap.add_argument("--bass-inst", default="bass")
    ap.add_argument("--assign", action="append", default=[], metavar="PAT=INST",
                    help="force INST when the track name contains PAT (case-insensitive); repeatable")
    ap.add_argument("--skip", action="append", default=[], metavar="PAT", help="skip matching tracks; repeatable")
    ap.add_argument("--vol", action="append", default=[], metavar="INST=VOL", help="override the default volume; repeatable")
    ap.add_argument("--drum-map", default="36=basedrum,38=snare,40=snare",
                    help="GM pitch→instrument; anything unlisted goes to hat (default 36=basedrum,38=snare,40=snare)")
    ap.add_argument("--no-fold", action="store_true", help="do not fold octaves (leave it to generate.py to clamp and warn)")
    ap.add_argument("--force", action="store_true", help="proceed even if the #speed time resolution is unusable")
    ap.add_argument("--report", default=None, help="write the arrangement decision report as markdown")
    a = ap.parse_args()

    # Time resolution: the host does nbs_s += #speed every tick and the tree window is 80×t, so note t
    # fires at game tick 80t/#speed; 1 game tick = 1/tick_rate s, hence 1 t unit = 80/(#speed × tick_rate) s.
    # t equals the game tick only when #speed=80; a larger tick_rate means a finer grid (20→50ms, 80→12.5ms).
    R = a.tick_rate
    res_ms = 80000.0 / (a.speed * R)
    if res_ms > 100.0 and not a.force:
        sys.exit("the time resolution for #speed %d + tick_rate %d is 1 t = %.0f ms (%.2f s per step), "
                 "which smears the whole song into mush; unusable in practice.\n"
                 "  the host does nbs_s += #speed every tick (tree window 80×t), 1 game tick = 1/tick_rate s;\n"
                 "  default #speed 80 + tick_rate 20 → t is the game tick (50 ms). Add --force if you really want this."
                 % (a.speed, R, res_ms, res_ms / 1000.0))
    if R not in (20, 80) and res_ms < 50.0:
        print("note: the grid for tick_rate %d is %.2f ms; make sure the host really ran /tick rate %d" % (R, res_ms, R))

    for inst in (a.chord_inst, a.bass_inst) + (() if a.lead_inst == "auto" else (a.lead_inst,)):
        if inst not in INSTRUMENTS:
            sys.exit("unknown instrument: %s (see the whitelist in references/instruments.md)" % inst)
        if inst in HEADS:
            sys.exit("head instruments have no pitch, so they cannot be used for melody: %s" % inst)
        if vtuple(a.mc_version) < vtuple(INSTRUMENTS[inst]["min"]):
            sys.exit("instrument %s needs MC %s+ (target %s)" % (inst, INSTRUMENTS[inst]["min"], a.mc_version))

    drum_map = {}
    for kv in a.drum_map.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            drum_map[int(k.strip())] = v.strip()
    assigns = []
    for kv in a.assign:
        if "=" not in kv:
            sys.exit("--assign needs the PAT=INST form: %s" % kv)
        p, i = kv.split("=", 1)
        if i.strip() not in INSTRUMENTS:
            sys.exit("unknown instrument: %s" % i)
        assigns.append((p.strip().lower(), i.strip()))
    vovers = {}
    for kv in a.vol:
        if "=" in kv:
            k, v = kv.split("=", 1)
            vovers[k.strip()] = float(v)

    name = sanitize(a.name or os.path.splitext(os.path.basename(a.midi))[0])
    path = a.path or ("music/" + name)
    m = read_midi(a.midi)
    bpm = m.bpm_at(0)
    tps_midi = m.ticks_per_second(0)

    def game_tick_of(midi_tick):
        return m.sec_at(midi_tick) * R

    # The host does nbs_s += S every tick and the tree window is 80t → note t fires at game tick 80t/S;
    # 1 game tick = 1/R s → to place notes on a "seconds" grid, t = seconds × R × S / 80
    def to_t(midi_tick):
        g = game_tick_of(midi_tick)
        return int(round(g * a.speed / 80.0)), g

    events = collections.defaultdict(dict)          # t -> (inst, midi) -> vol
    stats = collections.Counter()
    errs, folds = [], collections.Counter()
    mapping_rows = []
    tick_src = {}                                   # t -> first MIDI tick landing on this t (for the spot-check table)

    def add(midi_tick, inst, midi, vol, tag):
        t, g = to_t(midi_tick)
        base = INSTRUMENTS[inst]["base"]
        lo, hi = base, base + 24
        n = 0
        if not a.no_fold:
            while midi > hi:
                midi -= 12
                n -= 1
            while midi < lo:
                midi += 12
                n += 1
        if n:
            stats["folded_" + inst] += 1
            folds[n] += 1
        key = (inst, midi)
        if key in events[t]:
            stats["dupe_dropped"] += 1
            return
        if t < 0:
            stats["dropped_negative_t"] += 1
            return
        events[t][key] = vol
        tick_src.setdefault(t, midi_tick)
        stats["notes_" + tag] += 1
        errs.append(abs(80.0 * t / a.speed - g) / R * 1000.0)   # difference between the actual and ideal onset time (ms)

    # ---------------- track classification ----------------
    used_tracks = []
    for tr in m.tracks:
        if not tr.notes:
            continue
        low = tr.name.lower()
        if any(k.lower() in low for k in a.skip):
            mapping_rows.append((tr, "—", "skipped by --skip", 0, 0, "-"))
            continue
        forced = next((i for p, i in assigns if p in low), None)
        is_drum = (9 in tr.channels) or any(k in low for k in DRUM_KEYWORDS)
        is_bass = any(k in low for k in BASS_KEYWORDS)

        if forced:
            inst = forced
            for n in tr.notes:
                add(n.tick, inst, n.pitch, vol_of(inst, vovers), "assigned")
            mapping_rows.append((tr, inst, "set by --assign", len(tr.notes),
                                 stats["folded_" + inst], vol_of(inst, vovers)))
        elif is_drum:
            cnt = collections.Counter()
            for n in tr.notes:
                inst = drum_map.get(n.pitch, "hat")
                if inst not in INSTRUMENTS:
                    sys.exit("unknown instrument in --drum-map: %s" % inst)
                add(n.tick, inst, 54, vol_of(inst, vovers), "drum")
                cnt[inst] += 1
            mapping_rows.append((tr, "drums" + str(dict(cnt)), "channel 9 / track name contains a drum keyword",
                                 len(tr.notes), 0, "see the volume table"))
        elif is_bass:
            inst = a.bass_inst
            for n in tr.notes:
                add(n.tick, inst, n.pitch, vol_of(inst, vovers), "bass")
            mapping_rows.append((tr, inst, "track name contains a bass keyword", len(tr.notes),
                                 stats["folded_" + inst], vol_of(inst, vovers)))
        else:
            ps = [n.pitch for n in tr.notes]
            lead_inst = a.lead_inst
            picked = None
            if lead_inst == "auto":
                # if the whole track's pitch range fits a single instrument (within 25 semitones) do not
                # split; take the first that fits in preference order
                for cand in ("pling", "flute", "bit", "harp", "bell", "chime"):
                    lo_, hi_ = INSTRUMENTS[cand]["base"], INSTRUMENTS[cand]["base"] + 24
                    if min(ps) >= lo_ and max(ps) <= hi_:
                        picked = cand
                        break
            if picked:
                for n in tr.notes:
                    add(n.tick, picked, n.pitch, vol_of(picked, vovers), "lead")
                mapping_rows.append((tr, picked, "whole-track pitch range %d..%d fits a single instrument (auto)"
                                     % (min(ps), max(ps)), len(tr.notes), stats["folded_" + picked],
                                     vol_of(picked, vovers)))
            else:
                # split lead/chords; in auto mode pick the instrument with the fewest octave folds for the high part
                hi_inst = lead_inst
                if hi_inst == "auto":
                    hi = [p for p in ps if p >= a.lead_split] or [max(ps)]
                    best, bestn = "flute", None
                    for cand in ("flute", "pling", "bit", "harp", "bell"):
                        lo_, hh_ = INSTRUMENTS[cand]["base"], INSTRUMENTS[cand]["base"] + 24
                        n_fold = sum(1 for p in hi if not (lo_ <= p <= hh_))
                        if bestn is None or n_fold < bestn:
                            best, bestn = cand, n_fold
                    hi_inst = best
                lead = chord = 0
                for n in tr.notes:
                    if n.pitch >= a.lead_split:
                        add(n.tick, hi_inst, n.pitch, vol_of(hi_inst, vovers), "lead")
                        lead += 1
                    else:
                        add(n.tick, a.chord_inst, n.pitch, vol_of(a.chord_inst, vovers), "chord")
                        chord += 1
                mapping_rows.append((tr, "%s + %s" % (hi_inst, a.chord_inst),
                                     "split at pitch %d (>=%d lead %d notes / rest %d notes)"
                                     % (a.lead_split, a.lead_split, lead, chord),
                                     len(tr.notes), stats["folded_" + hi_inst] + stats["folded_" + a.chord_inst],
                                     "%s / %s" % (vol_of(hi_inst, vovers), vol_of(a.chord_inst, vovers))))
        used_tracks.append(tr)

    if not events:
        sys.exit("no notes were produced")

    ticks = sorted(events)
    maxt = ticks[-1]
    poly = max(len(v) for v in events.values())

    # ---------------- write song.json ----------------
    # Track order: preference order first (deduplicated!), then append any used instrument missing from
    # the preference list (so no track is dropped)
    pref = []
    for x in [a.lead_inst, a.chord_inst, a.bass_inst, "basedrum", "snare", "hat",
              "pling", "bit", "harp", "bell", "chime", "xylophone", "banjo",
              "iron_xylophone", "cow_bell", "didgeridoo", "flute", "guitar"]:
        if x != "auto" and x not in pref:
            pref.append(x)
    used = set(i for v in events.values() for (i, _m) in v)
    order = [i for i in pref if i in used] + sorted(used - set(pref))
    tracks = []
    for inst in order:
        notes = [{"t": t, "midi": mid, "vol": v}
                 for t in ticks for (i, mid), v in sorted(events[t].items()) if i == inst]
        if notes:
            tracks.append({"name": inst if inst not in ("basedrum", "snare", "hat") else "drums_" + inst,
                           "include": True, "instrument_default": inst, "notes": notes})
    song = {"meta": {
        "name": name, "namespace": a.namespace, "path": path, "song_id": a.song_id,
        "mc_version": a.mc_version, "style": a.style, "time_unit": "nbs_s_units",
        "speed": a.speed, "auto_stop": True, "next_song": None, "mute_tag": "no_music",
        "_source": os.path.basename(a.midi),
        "_timeline": "t = game tick (1/%d s); host #speed nbs_s = %d; tree window 80*t" % (R, a.speed),
        "_tick_rate": R},
        "tracks": tracks}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(song, f, ensure_ascii=False)
    total = sum(len(t["notes"]) for t in tracks)

    errs.sort()
    print("song.json → %s" % a.out)
    print("  source: %s  %.3f BPM  duration %.2fs  raw note-on %d" % (os.path.basename(a.midi), bpm,
                                                                     m.sec_at(m.last_note_tick()), m.note_count))
    print("  output: %d notes / %d note ticks / last tick %d (%.1fs) / max %d playsound on one tick"
          % (total, len(ticks), maxt, maxt / float(R), poly))
    print("  timeline: tick_rate=%d (1 t = %.2f ms)  t = round(seconds × %d × %d/80) = round(seconds × %.4g)"
          % (R, res_ms, R, a.speed, R * a.speed / 80.0))
    print("  quantization error: median %.1f ms / p90 %.1f ms / max %.1f ms"
          % (errs[len(errs) // 2], errs[int(len(errs) * 0.9)], errs[-1]))
    for k in sorted(stats):
        print("    %-20s %d" % (k, stats[k]))
    if folds:
        print("  octave folding: %s (+1 = raised one octave to enter the instrument's range)"
              % ", ".join("%+d×%d" % (k, v) for k, v in sorted(folds.items())))
    if a.speed != 80 or R != 20:
        print("  ⚠ the host must satisfy: #speed nbs_s = %d (already written in init.mcfunction)%s"
              % (a.speed, ", and run /tick rate %d manually after entering the game (rejoining the world resets it)" % R if R != 20 else ""))

    # ---------------- arrangement decision report ----------------
    if a.report:
        L = []
        L.append("# Arrangement decision report (generated by midi_to_song.py)\n")
        L.append("## Source\n")
        L.append("- File: `%s`" % os.path.basename(a.midi))
        L.append("- Tempo: **%.3f BPM**; division %d ticks/quarter note; duration %.2f s" % (bpm, m.division, m.sec_at(m.last_note_tick())))
        L.append("- Raw note-on: %d (note-on only, no on/off pairing)" % m.note_count)
        L.append("- Tempo changes: %s\n" % ("single tempo" if len(m.tempos) == 1 else
                                            " | ".join("%.3f BPM @%d" % (60e6 / u, t) for t, u in m.tempos)))
        L.append("## Part mapping\n")
        L.append("| Track | Channel | Raw notes | Mapped to | Criterion | Volume | Octave folds |")
        L.append("|---|---|---|---|---|---|---|")
        for tr, inst, why, cnt, foldn, vol in mapping_rows:
            L.append("| %s | %s | %d | %s | %s | %s | %d |"
                     % (tr.name, ",".join(str(c) for c in sorted(tr.channels)) or "-", cnt,
                        inst, why, vol, foldn))
        L.append("")
        L.append("## Output\n")
        L.append("- Notes %d, note ticks %d, last tick %d (%.1f s), max %d playsound on one tick (limit 255)"
                 % (total, len(ticks), maxt, maxt / float(R), poly))
        L.append("- Dedupe key = (tick, instrument, pitch): chords of the same instrument on the same tick are **all kept**; duplicates dropped this run: %d"
                 % stats["dupe_dropped"])
        L.append("- Pitch-range folding: %s\n" % (", ".join("%+d octave(s) ×%d note(s)" % (k, v) for k, v in sorted(folds.items()))
                                                  or "none (every note was already inside its instrument's range)"))
        L.append("## Timeline\n")
        L.append("- `time_unit = nbs_s_units`, `speed = %d`, host `tick_rate = %d`" % (a.speed, R))
        L.append("- 1 t unit = 80/(#speed × tick_rate) = **%.2f ms**; t = round(seconds × %d × %d/80)"
                 % (res_ms, R, a.speed))
        L.append("- Quantization error this run: median %.1f ms / max %.1f ms" % (errs[len(errs) // 2], errs[-1]))
        L.append("- 1 MIDI tick = %.4f s; 1 t unit = %.1f MIDI tick" % (1.0 / tps_midi, tps_midi * res_ms / 1000.0))
        L.append("- The host must satisfy `#speed nbs_s = %d`, otherwise the whole song's tempo is wrong (the tree window 80×t goes with it)" % a.speed)
        if R != 20:
            L.append("- ⚠ **you must run `/tick rate %d` manually after entering the game** (1.20.3+; leaving and re-entering resets it to 20, "
                     "otherwise the whole song plays %d times slower)" % (R, R // 20))
        L.append("")
        L.append("## Spot check (first 8 note ticks)\n")
        L.append("| MIDI tick | Seconds | Game tick | Written t | Notes |")
        L.append("|---|---|---|---|---|")
        for t in ticks[:8]:
            mt = tick_src.get(t, 0)
            sec = m.sec_at(mt)
            insts = "+".join(sorted(set(i for i, _ in events[t])))
            L.append("| %d | %.4f | %.2f | %d | %s |" % (mt, sec, sec * 20.0, t, insts))
        L.append("")
        L.append("## Before delivery\n")
        L.append("```bash")
        L.append("python3 scripts/generate.py %s -o out/%s" % (a.out, path))
        L.append("python3 scripts/validate_pack.py --pack out --namespace %s --song %s --song-id %d --speed %d --mc-version %s"
                 % (a.namespace, name, a.song_id, a.speed, a.mc_version))
        L.append("```")
        with open(a.report, "w", encoding="utf-8") as f:
            f.write("\n".join(L) + "\n")
        print("  arrangement decision report → %s" % a.report)


if __name__ == "__main__":
    main()
