#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-delivery self-check: tree <-> notes consistency, instrument whitelist/pitch range, CRLF, tags,
song_id, plus a tree state-machine simulation proving each note tick fires exactly once on the correct game tick.

Usage (standalone datapack):
    python3 scripts/validate_pack.py --pack out --namespace minecraft --song lemon \
        --song-id 8 --speed 80 --mc-version 26.2
Usage (lemon compatible mode, where the deliverable is just the song folder):
    python3 scripts/validate_pack.py --pack out/music/lemon --song lemon --song-id 8

Exit code 0 if everything passes, otherwise 1. Standard library only.
"""
import argparse, collections, json, math, os, re, sys

try:            # Windows consoles default to GBK: let non-GBK characters degrade to ? instead of raising
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# instrument whitelist: inst -> (use-count baseline MIDI, minimum MC version)
INSTRUMENTS = {
    "harp": (54, "1.13"), "bass": (30, "1.13"), "basedrum": (54, "1.13"),
    "snare": (54, "1.13"), "hat": (54, "1.13"), "bell": (78, "1.13"),
    "chime": (78, "1.13"), "flute": (66, "1.13"), "guitar": (42, "1.13"),
    "xylophone": (78, "1.13"), "iron_xylophone": (54, "1.14"), "cow_bell": (54, "1.14"),
    "didgeridoo": (30, "1.14"), "bit": (54, "1.14"), "banjo": (54, "1.14"),
    "pling": (54, "1.14"), "skeleton": (54, "1.20"), "wither_skeleton": (54, "1.20"),
    "zombie": (54, "1.20"), "creeper": (54, "1.20"), "piglin": (54, "1.20"),
    "dragon": (54, "1.20"), "trumpet": (54, "26.1"), "trumpet_exposed": (54, "26.1"),
    "trumpet_weathered": (42, "26.1"), "trumpet_oxidized": (42, "26.1"),
}
HEADS = ("skeleton", "wither_skeleton", "zombie", "creeper", "piglin", "dragon")
# sound event name -> instrument
SOUND2INST = {
    "block.note_block.harp": "harp", "block.note_block.bass": "bass",
    "block.note_block.basedrum": "basedrum", "block.note_block.snare": "snare",
    "block.note_block.hat": "hat", "block.note_block.bell": "bell",
    "block.note_block.chime": "chime", "block.note_block.flute": "flute",
    "block.note_block.guitar": "guitar", "block.note_block.xylophone": "xylophone",
    "block.note_block.iron_xylophone": "iron_xylophone",
    "block.note_block.cow_bell": "cow_bell", "block.note_block.didgeridoo": "didgeridoo",
    "block.note_block.bit": "bit", "block.note_block.banjo": "banjo",
    "block.note_block.pling": "pling",
    "block.note_block.imitate.skeleton": "skeleton",
    "block.note_block.imitate.wither_skeleton": "wither_skeleton",
    "block.note_block.imitate.zombie": "zombie",
    "block.note_block.imitate.creeper": "creeper",
    "block.note_block.imitate.piglin": "piglin",
    "block.note_block.imitate.ender_dragon": "dragon",
    "block.note_block.trumpet": "trumpet", "block.note_block.trumpet_exposed": "trumpet_exposed",
    "block.note_block.trumpet_weathered": "trumpet_weathered",
    "block.note_block.trumpet_oxidized": "trumpet_oxidized",
}

PS_RE = re.compile(r"execute as @a\[tag=!(\S+?)\] at @s run playsound minecraft:(\S+) voice @s "
                   r"\^0 \^ \^ (\S+) (\S+) 1$")
LEAF_RE = re.compile(r"^execute if score music_progress nbs_s matches (\d+)\.\.(\d+) "
                     r"if score music_progress nbs_t matches \.\.(-?\d+) run function (\S+)/notes/(\d+)$")
NODE_RE = re.compile(r"^execute if score music_progress nbs_s matches (\d+)\.\.(\d+) "
                     r"run function (\S+)/tree/(\d+_\d+)$")
SETT_RE = re.compile(r"^scoreboard players set music_progress nbs_t (-?\d+)$")
STOP_RE = re.compile(r"^function (\S+)/stop$")


def vtuple(v):
    return tuple(int(x) for x in str(v).split("."))


def read_text(path, mode="r"):
    with open(path, mode, encoding="utf-8", newline="") as f:
        return f.read()


def locate(pack, ns, path, song):
    """Return (song directory, datapack root or None)."""
    cand = os.path.join(pack, "data", ns, "function", path)
    if os.path.isdir(os.path.join(cand, "notes")) and os.path.isdir(os.path.join(cand, "tree")):
        return cand, pack
    if os.path.isdir(os.path.join(pack, "notes")) and os.path.isdir(os.path.join(pack, "tree")):
        return pack, None                       # lemon compatible mode: the deliverable is the song folder
    for dp, dns, _ in os.walk(pack):
        if os.path.basename(dp) == song and "notes" in dns and "tree" in dns:
            return dp, None                      # song folder found deeper in the tree; not treated as a pack root
    return None, None


def main():
    ap = argparse.ArgumentParser(description="pre-delivery self-check for a redstone music datapack")
    ap.add_argument("--pack", required=True, help="datapack root, or the song folder in lemon compatible mode")
    ap.add_argument("--namespace", default="minecraft")
    ap.add_argument("--path", default=None, help="function path, defaults to music/<song>")
    ap.add_argument("--song", default=None, help="song name (used for the default path and messages)")
    ap.add_argument("--song-id", type=int, default=None, help="music_type value that should appear in play/tick")
    ap.add_argument("--speed", type=int, default=80, help="value of #speed nbs_s, defaults to 80")
    ap.add_argument("--mc-version", default=None, help="target MC version, used to check instruments and pack.mcmeta syntax")
    ap.add_argument("--no-simulate", action="store_true", help="skip the tree state-machine simulation")
    a = ap.parse_args()
    if not a.song:
        a.song = os.path.basename(os.path.normpath(a.pack))
    path = a.path or ("music/" + a.song)
    full = "%s:%s" % (a.namespace, path)

    fail, warn = [], []
    song_dir, pack_root = locate(a.pack, a.namespace, path, a.song)
    if not song_dir:
        print("FAIL: no song directory containing notes/ and tree/ was found under %s (use --path to point at it)" % a.pack)
        return 1
    print("song directory: %s" % song_dir)

    notes_dir = os.path.join(song_dir, "notes")
    tree_dir = os.path.join(song_dir, "tree")
    notes = sorted(int(f[:-11]) for f in os.listdir(notes_dir) if f.endswith(".mcfunction"))
    trees = sorted(f[:-11] for f in os.listdir(tree_dir) if f.endswith(".mcfunction"))
    if not notes:
        print("FAIL: notes/ is empty")
        return 1

    # ---- 1. CRLF ----
    for dp, _, fs in os.walk(os.path.dirname(song_dir) if pack_root else song_dir):
        if pack_root and not dp.startswith(pack_root):
            continue
        for fn in fs:
            if not fn.endswith(".mcfunction"):
                continue
            p = os.path.join(dp, fn)
            b = open(p, "rb").read()
            if b"\n" in b and b"\r\n" not in b:
                fail.append("LF line endings (should be CRLF): %s" % p)

    # ---- 2. tree references notes exactly once (a leaf must be 1 wide, otherwise the second tick of an
    #         adjacent pair (2k,2k+1) goes silent) ----
    ref = collections.Counter()
    nodes = {}
    for name in trees:
        lines = [l for l in read_text(os.path.join(tree_dir, name + ".mcfunction")).split("\r\n") if l.strip()]
        nodes[name] = []
        for ln in lines:
            m = NODE_RE.match(ln)
            if m:
                nodes[name].append(("node", int(m.group(1)), int(m.group(2)), m.group(4)))
                continue
            m = LEAF_RE.match(ln)
            if m:
                nodes[name].append(("leaf", int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(5))))
                ref[int(m.group(5))] += 1
                continue
            fail.append("tree/%s has an unparseable line: %s" % (name, ln))
    bad_ref = [t for t in notes if ref[t] != 1]
    if bad_ref:
        fail.append("notes referenced by tree != 1 time: %d (first 10: %s) —— 0 means silent forever; "
                    "the most common cause is a leaf written 2 wide (see references/format_spec.md §A)"
                    % (len(bad_ref), bad_ref[:10]))
    ghost = [t for t in ref if t not in notes]
    if ghost:
        fail.append("tree references notes that do not exist: %s" % ghost[:10])

    # ---- 3. tree root reachability + dangling child nodes ----
    tick_path = os.path.join(song_dir, "tick.mcfunction")
    root = None
    if os.path.isfile(tick_path):
        for m in re.finditer(r"function %s/tree/(\d+_\d+)" % re.escape(full),
                             read_text(tick_path)):
            root = m.group(1)
    if root is None:
        warn.append("could not find a tree root call in %s/tick.mcfunction (in lemon compatible mode the host may call it)" % path)
    for name, items in nodes.items():
        for it in items:
            if it[0] == "node" and it[3] not in nodes:
                fail.append("tree/%s points to a child node that does not exist: %s" % (name, it[3]))
    reachable = set()
    if root and root in nodes:
        stack = [root]
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            for it in nodes.get(cur, []):
                if it[0] == "node":
                    stack.append(it[3])
        un = sorted(set(trees) - reachable)
        if un:
            fail.append("tree nodes unreachable from root %s: %d (first 10: %s)" % (root, len(un), un[:10]))
    elif root:
        fail.append("tree root %s does not exist" % root)

    # ---- 4. playsound lines: whitelist, pitch range, volume ----
    vols = collections.defaultdict(set)
    spans = collections.defaultdict(lambda: [99, -1])
    nlines = 0
    for t in notes:
        for ln in read_text(os.path.join(notes_dir, "%d.mcfunction" % t)).split("\r\n"):
            if not ln.strip() or ln.startswith("scoreboard") or ln.startswith("function"):
                continue
            m = PS_RE.match(ln)
            if not m:
                fail.append("notes/%d has an unexpected line: %s" % (t, ln))
                continue
            nlines += 1
            ev, vol, pitch = m.group(2), float(m.group(3)), float(m.group(4))
            inst = SOUND2INST.get(ev)
            if inst is None:
                fail.append("notes/%d uses a sound effect outside the whitelist: %s" % (t, ev))
                continue
            if a.mc_version and vtuple(a.mc_version) < vtuple(INSTRUMENTS[inst][1]):
                fail.append("notes/%d: %s needs MC %s+ (target %s)" % (t, inst, INSTRUMENTS[inst][1], a.mc_version))
            if not 0.5 <= pitch <= 2.0:
                fail.append("notes/%d has pitch=%s outside [0.5,2.0]" % (t, pitch))
                continue
            uc = int(round(12 + 12 * math.log(pitch, 2)))
            if not 0 <= uc <= 24:
                fail.append("notes/%d: %s use-count=%d outside [0,24] (octave folding not applied?)" % (t, inst, uc))
            if inst in HEADS:
                warn.append("notes/%d uses the head instrument %s (ignores pitch)" % (t, inst))
            vols[inst].add(vol)
            spans[inst][0] = min(spans[inst][0], uc)
            spans[inst][1] = max(spans[inst][1], uc)

    # ---- 5. play/stop/tick song_id and auto_stop on the last tick ----
    play_p, stop_p, tick_p = (os.path.join(song_dir, x) for x in
                              ("play.mcfunction", "stop.mcfunction", "tick.mcfunction"))
    sid = None
    if os.path.isfile(play_p):
        m = re.search(r"scoreboard players set music_progress music_type (-?\d+)", read_text(play_p))
        sid = int(m.group(1)) if m else None
    if a.song_id is not None:
        if sid != a.song_id:
            fail.append("play.mcfunction has song_id=%s, expected %d" % (sid, a.song_id))
        if os.path.isfile(tick_p) and ("matches %d run" % a.song_id) not in read_text(tick_p):
            fail.append("tick.mcfunction has no if music_type matches %d guard" % a.song_id)
        if os.path.isfile(stop_p) and ("matches %d run" % a.song_id) in read_text(stop_p):
            warn.append("stop.mcfunction also carries a song_id guard (upstream convention: stop is unguarded)")
    last = [l for l in read_text(os.path.join(notes_dir, "%d.mcfunction" % notes[-1])).split("\r\n") if l.strip()]
    if last and not STOP_RE.match(last[-1]):
        fail.append("last tick notes/%d does not end with function .../stop on its last line" % notes[-1])

    # ---- 6. pack.mcmeta and tags (optional: lemon compatible deliverables never had them) ----
    if pack_root:
        mc = os.path.join(pack_root, "pack.mcmeta")
        if not os.path.isfile(mc):
            fail.append("missing pack.mcmeta")
        else:
            try:
                p = json.loads(read_text(mc))["pack"]
            except Exception as e:
                p = None
                fail.append("pack.mcmeta is not valid JSON: %s" % e)
            if p is not None:
                modern = bool(a.mc_version and vtuple(a.mc_version) >= (1, 21, 9))
                if modern or ("min_format" in p or "max_format" in p):
                    if "min_format" not in p or "max_format" not in p:
                        fail.append("≥1.21.9 must write min_format and max_format (arrays of [major,minor])")
                    else:
                        for k in ("min_format", "max_format"):
                            if not (isinstance(p[k], list) and len(p[k]) == 2 and all(isinstance(x, int) for x in p[k])):
                                fail.append("%s must be two integers [major,minor] (a decimal 107.1 is not allowed): %r" % (k, p[k]))
                        if p["min_format"] != p["max_format"]:
                            warn.append("min_format %s != max_format %s (only correct when genuinely spanning versions)" % (p["min_format"], p["max_format"]))
                    for k in ("pack_format", "supported_formats"):
                        if k in p:
                            fail.append("the modern ≥1.21.9 syntax must not contain %s any more" % k)
                else:
                    if "pack_format" not in p:
                        fail.append("≤1.21.8 requires pack_format")
                    for k in ("min_format", "max_format"):
                        if k in p:
                            fail.append("≤1.21.8 must not contain %s" % k)
        for tag, target in (("load", "%s/init" % full), ("tick", "%s/tick" % full)):
            tf = os.path.join(pack_root, "data", a.namespace, "tags", "function", tag + ".json")
            if not os.path.isfile(tf):
                warn.append("no data/%s/tags/function/%s.json (safe to ignore in lemon compatible mode)" % (a.namespace, tag))
                continue
            try:
                vals = json.loads(read_text(tf)).get("values", [])
            except Exception as e:
                fail.append("%s is not valid JSON: %s" % (tf, e))
                continue
            for v in vals:
                ns, _, pth = str(v).partition(":")
                if not os.path.isfile(os.path.join(pack_root, "data", ns, "function", pth + ".mcfunction")):
                    fail.append("tags/function/%s.json points to a function that does not exist: %s" % (tag, v))
            if target not in vals:
                warn.append("tags/function/%s.json does not contain %s" % (tag, target))

    # ---- 7. tree state-machine simulation: does each tick fire exactly once on the correct game tick ----
    fired = collections.defaultdict(list)
    sim_note = "-"
    if not a.no_simulate and root and root in nodes:
        by_name = nodes
        maxt = notes[-1]
        # simulate the state "play.mcfunction has just run": nbs_s=0, nbs_t=-1 (None = unset after reset = matches no range)
        state = {"nbs_s": 0, "nbs_t": -1}

        def call_notes(t):
            fired[t].append(T)
            ln = [l for l in read_text(os.path.join(notes_dir, "%d.mcfunction" % t)).split("\r\n") if l.strip()]
            m = SETT_RE.match(ln[-1]) if ln else None
            if m:
                state["nbs_t"] = int(m.group(1))
            elif ln and STOP_RE.match(ln[-1]):
                state["nbs_s"] = 0
                state["nbs_t"] = None

        def call_tree(name):
            for it in by_name.get(name, []):
                if not (it[1] <= state["nbs_s"] <= it[2]):
                    continue
                if it[0] == "node":
                    call_tree(it[3])
                else:
                    g, t = it[3], it[4]
                    if state["nbs_t"] is not None and state["nbs_t"] <= g:
                        call_notes(t)

        for T in range(1, maxt + 4):          # run a few extra ticks to confirm nothing fires twice
            state["nbs_s"] += a.speed
            call_tree(root)
        once = [t for t in notes if len(fired[t]) != 1]
        if once:
            fail.append("simulation result: %d notes fire != 1 time (first 10: %s) —— 0 = silent, >1 = played twice"
                        % (len(once), [(t, len(fired[t])) for t in once[:10]]))
        wrong = []
        for t in notes:
            if len(fired[t]) == 1:
                # tick.mcfunction does nbs_s += #speed before calling the tree; the leaf window is 80t..80t+160
                # → the first matching T = ceil(80t/speed), and T is at least 1 (the t=0 note also fires on the first tick)
                exp = max(1, (80 * t + a.speed - 1) // a.speed)
                if fired[t][0] != exp:
                    wrong.append((t, fired[t][0], exp))
        if wrong:
            warn.append("%d notes fire more than 0 ticks away from the expected moment (first 5: %s)"
                        % (len(wrong), wrong[:5]))
        sim_note = "every tick fires exactly once" if not once else "abnormal"

    # ---- report
    print("notes: %d   tree nodes: %d   reachable: %d   playsound lines: %d"
          % (len(notes), len(trees), len(reachable), nlines))
    print("tick range: %d..%d  duration %.1fs   #speed=%d" % (notes[0], notes[-1], notes[-1] / 20.0, a.speed))
    print("volume per instrument: %s" % {k: sorted(v) for k, v in sorted(vols.items())})
    print("use-count range per instrument: %s"
          % {k: tuple(v) for k, v in sorted(spans.items()) if v[1] >= 0})
    if not a.no_simulate:
        print("tree state-machine simulation: %s" % sim_note)
    for w in warn:
        print("WARN: %s" % w)
    if fail:
        print("\nFAIL (%d):" % len(fail))
        for x in fail[:40]:
            print("  - %s" % x)
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
