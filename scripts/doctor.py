#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Redstone music datapack health check / one-shot "why is there no sound" troubleshooting.

Division of labour with validate_pack.py: validate_pack.py is the **hard gate before delivery** (for CI:
any failure means exit code 1); doctor.py is the **human-facing troubleshooting wizard** — it prints
each item with ✓/✗ and gives a "how to fix" line under every ✗, then ends with "what to type in game,
in order" and a "symptom → cause" quick reference. Internally it calls validate_pack.py for the deep check.

Usage:
    python3 scripts/doctor.py --pack out/m3                      # health-check a datapack directory
    python3 scripts/doctor.py --pack m3-redstone-music-26.2.zip  # health-check a zip directly (structure checks only)
    python3 scripts/doctor.py --pack out/m3 --mc-version 26.2 --song m3 --song-id 9 --speed 80
    python3 scripts/doctor.py --pack out/m3 --world-dir "<world>/datapacks"   # also confirm it is installed in the world
Standard library only.
"""
import argparse, json, os, subprocess, sys, zipfile

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATE = os.path.join(HERE, "validate_pack.py")
# A GBK console cannot tell ✓/✗ apart (both become ?), so fall back to ASCII markers that still read at a glance
try:
    "✓".encode(sys.stdout.encoding or "utf-8")
    OK, BAD, WARN = "✓", "✗", "!"
except Exception:
    OK, BAD, WARN = "[OK]", "[X]", "[!]"

problems = []


def item(ok, title, fix=None, warn=False):
    mark = OK if ok else (WARN if warn else BAD)
    print(" %s %s" % (mark, title))
    if not ok and fix:
        print("     → %s" % fix)
    if not ok and not warn:
        problems.append(title)
    return ok


class Src(object):
    """Unify "directory" and "zip" behind one read interface."""

    def __init__(self, path):
        self.path = path
        self.zip = zipfile.ZipFile(path) if zipfile.is_zipfile(path) else None
        self.names = set(self.zip.namelist()) if self.zip else None

    def has(self, rel):
        if self.zip:
            return rel in self.names or (rel + "/") in self.names
        return os.path.exists(os.path.join(self.path, rel))

    def read(self, rel):
        if self.zip:
            return self.zip.read(rel).decode("utf-8", "replace")
        with open(os.path.join(self.path, rel), encoding="utf-8", newline="") as f:
            return f.read()


def main():
    ap = argparse.ArgumentParser(description="redstone music datapack health check / no-sound troubleshooting")
    ap.add_argument("--pack", required=True, help="datapack directory or zip")
    ap.add_argument("--mc-version", default=None, help="target MC version (leave empty for generic checks only)")
    ap.add_argument("--namespace", default="minecraft")
    ap.add_argument("--path", default=None, help="function path, defaults to music/<song>")
    ap.add_argument("--song", default=None)
    ap.add_argument("--song-id", type=int, default=None)
    ap.add_argument("--speed", type=int, default=80)
    ap.add_argument("--world-dir", default=None, help="the world's datapacks directory, used to confirm it is installed in the world")
    a = ap.parse_args()
    if not a.song:
        a.song = os.path.splitext(os.path.basename(os.path.normpath(a.pack)))[0]
    path = a.path or ("music/" + a.song)
    full = "%s:%s" % (a.namespace, path)

    print("=== redstone music datapack health check: %s ===" % a.pack)
    print("    target version %s | namespace %s | path %s | song_id %s | #speed %s\n"
          % (a.mc_version or "(not specified)", a.namespace, path, a.song_id, a.speed))

    src = Src(a.pack)
    if src.zip:
        print("[0] input is a zip —— structure and metadata checks only; extract it and run again for the deep check")
        print("     pack.mcmeta must be at the root of the zip (many archivers add an extra folder level)")

    # ---------- 1. structure ----------
    print("\n[1] file structure")
    item(src.has("pack.mcmeta"), "pack.mcmeta is at the datapack root",
         "extract the zip and check for an extra folder level; pack.mcmeta must sit directly in the datapack root")
    modern = None
    if a.mc_version:
        vt = tuple(int(x) for x in a.mc_version.split("."))
        modern = vt >= (1, 21)
    for cand in (["function"] if modern is not False else ["functions"]) if modern is not None else ["function", "functions"]:
        if src.has("data/%s/%s/%s/play.mcfunction" % (a.namespace, cand, path)):
            fdir = cand
            break
    else:
        fdir = None
    item(fdir is not None, "song directory exists (data/%s/<%s>/%s/)" % (a.namespace, "function" if modern is not False else "functions", path),
         "make sure --song/--path match the -o directory you gave generate.py; from 1.21 the directory is the singular function/, and ≤1.20.4 uses the plural functions/")
    if fdir:
        for f in ("play", "stop", "tick"):
            item(src.has("data/%s/%s/%s/%s.mcfunction" % (a.namespace, fdir, path, f)),
                 "%s.mcfunction exists" % f, "regenerate with generate.py")
        if src.zip:
            n_notes = sum(1 for x in src.names if x.endswith(".mcfunction") and
                          x.startswith("data/%s/%s/%s/notes/" % (a.namespace, fdir, path)))
        else:
            nd = os.path.join(a.pack, "data", a.namespace, fdir, path, "notes")
            n_notes = len([x for x in os.listdir(nd) if x.endswith(".mcfunction")])
        item(n_notes > 0, "notes/ has %d files" % n_notes, "notes/ is empty: song.json has no notes, or generate.py never got to writing files")

    # ---------- 2. pack.mcmeta and version ----------
    print("\n[2] pack.mcmeta and target version")
    if src.has("pack.mcmeta"):
        try:
            pk = json.loads(src.read("pack.mcmeta"))["pack"]
        except Exception as e:
            pk = None
            item(False, "pack.mcmeta is valid JSON", "common traps: a trailing comma, curly quotes, a BOM. Validate it with json: %s" % e)
        if pk is not None:
            has_new = "min_format" in pk or "max_format" in pk
            has_old = "pack_format" in pk
            if a.mc_version and modern:
                item(has_new and not has_old, "≥1.21.9 uses min_format/max_format and no pack_format",
                     "≥1.21.9 (datapack format ≥82) must be written as {\"pack\":{\"min_format\":[107,1],"
                     "\"max_format\":[107,1],\"description\":\"...\"}}; keeping pack_format is judged incompatible. "
                     "Generating with make_datapack.py avoids this")
                if has_new:
                    ok_fmt = all(isinstance(pk.get(k), list) and len(pk[k]) == 2 and
                                 all(isinstance(y, int) for y in pk[k]) for k in ("min_format", "max_format"))
                    item(ok_fmt, "format is two integers [major,minor] (no decimal 107.1)",
                         "a decimal like 107.1 is not allowed; write [107, 1]")
            else:
                item(has_old and not has_new, "≤1.21.8 uses pack_format",
                     "≤1.21.8 uses \"pack_format\": <number>; min_format/max_format is the 1.21.9+ syntax")
            print("     (contents: %s)" % json.dumps(pk, ensure_ascii=False)[:150])

    # ---------- 3. tags / init / song_id ----------
    print("\n[3] engine tags, init and song_id")
    tag_dir = "data/minecraft/tags/%s" % (fdir or "function")
    has_tags = src.has(tag_dir + "/tick.json") and src.has(tag_dir + "/load.json")
    item(has_tags, "load.json / tick.json exist (standalone datapack mode)",
         "no tags = this song will not be driven automatically in game. If this is a lemon compatible "
         "deliverable meant to attach to an existing host pack, that is normal —— but the host must call %s/tick itself every tick" % full, warn=True)
    if has_tags:
        try:
            vals = json.loads(src.read(tag_dir + "/tick.json")).get("values", [])
        except Exception:
            vals = []
        item("%s/tick" % full in vals, "tick.json points to %s/tick" % full,
             "the path in a tag is written as <namespace>:<path> (no function/ directory, no .mcfunction)")
    if fdir and src.has("data/%s/%s/%s/init.mcfunction" % (a.namespace, fdir, path)):
        init = src.read("data/%s/%s/%s/init.mcfunction" % (a.namespace, fdir, path))
        item(("#speed nbs_s %d" % a.speed) in init.replace("  ", " "),
             "init.mcfunction sets #speed nbs_s = %d" % a.speed,
             "#speed unset → nbs_s gains 0 every tick → every note piles onto tick 0 (it sounds like a single 'tick' and then nothing)")
        for obj in ("music_type", "nbs_s", "nbs_t"):
            item(("objectives add %s" % obj) in init, "init created the scoreboard objective %s" % obj,
                 "a missing objective makes tick.mcfunction error out and the whole song silent")
    if fdir and src.has("data/%s/%s/%s/play.mcfunction" % (a.namespace, fdir, path)):
        pl = src.read("data/%s/%s/%s/play.mcfunction" % (a.namespace, fdir, path))
        got = None
        for ln in pl.splitlines():
            if "music_type" in ln and "set" in ln:
                got = ln.split()[-1]
        if a.song_id is not None:
            item(got == str(a.song_id), "play.mcfunction has song_id = %s (expected %s)" % (got, a.song_id),
                 "song_id mismatch → the if guard in tick.mcfunction never holds → completely silent")

    # ---------- 4. deep check (delegated to validate_pack.py) ----------
    print("\n[4] deep check (tree↔notes consistency + tree state-machine simulation)")
    if src.zip:
        print(" ! skipping this for zip input; extract first and run: python3 scripts/validate_pack.py --pack <directory> ...")
    else:
        cmd = [sys.executable, VALIDATE, "--pack", a.pack, "--namespace", a.namespace,
               "--song", a.song, "--speed", str(a.speed)]
        if a.path:
            cmd += ["--path", a.path]
        if a.song_id is not None:
            cmd += ["--song-id", str(a.song_id)]
        if a.mc_version:
            cmd += ["--mc-version", a.mc_version]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        out = r.stdout.decode("utf-8", "replace")
        item(r.returncode == 0, "validate_pack.py passed",
             "paste its output below to see which item fails; the most common cause is a leaf written 2 wide, which silences an adjacent tick")
        for ln in out.splitlines():
            if ln.startswith("FAIL") or ln.strip().startswith("-") or "ALL CHECKS" in ln:
                print("     %s" % ln.strip())

    # ---------- 5. is it installed in the world ----------
    if a.world_dir:
        print("\n[5] is it installed in the world")
        base = os.path.basename(os.path.normpath(a.pack))
        cand = os.path.join(a.world_dir, base)
        item(os.path.exists(cand), "the world's datapacks/ contains %s" % base,
             "after putting the zip (or the extracted folder) into %s you must /reload" % a.world_dir)
        if os.path.isdir(a.world_dir):
            others = [d for d in os.listdir(a.world_dir) if os.path.isdir(os.path.join(a.world_dir, d))]
            print("     datapacks/ currently holds: %s" % (", ".join(others) or "(empty)"))

    # ---------- 6. what to do in game ----------
    print("\n[6] type these in game, in this order (the wrong order means no sound)")
    print("     1) /reload                                  (re-run after changing any file)")
    print("     2) /datapack list                            (not listed = go back to [2] and check pack.mcmeta)")
    if a.mc_version and modern is False:
        print("     3) /tick rate defaults to 20; this song is made for #speed %d, no change needed" % a.speed)
    print("     3) /function %s/play" % full)
    print("     4) to stop: /function %s/stop" % full)
    print("     5) mute: /tag <player> add no_music")
    if a.mc_version and tuple(int(x) for x in a.mc_version.split(".")) >= (1, 20, 3):
        print("     * if you made it with --tick-rate 80, you must first run /tick rate 80 (leaving and rejoining resets it to 20)")

    # ---------- 7. symptom quick reference ----------
    print("\n[7] symptom → cause quick reference")
    for sym, cause in [
        ("it does not appear in /datapack list at all", "pack.mcmeta missing / invalid JSON / wrong version syntax (see [2])"),
        ("%s is missing from tab completion" % full, "function vs functions directory name swapped, or the tag was not read by /reload"),
        ("no sound at all after play", "① tick.json does not point to this song ② #speed unset ③ song_id mismatch ④ the player has the no_music tag"),
        ("it makes one sound and stops", "#speed nbs_s is 0 or missing → nbs_s never grows"),
        ("the whole song is the wrong speed (an integer multiple fast/slow)", "#speed differs from what it was made with; something made with --tick-rate needs /tick rate"),
        ("a few notes are silent", "a leaf written 2 wide (silences an adjacent tick); or a pitch outside the range was clamped; or same tick + same instrument + same pitch was deduplicated"),
        ("one pitch sounds wrong", "out of the pitch range it was clamped to the edge instead of folded by an octave —— confirm with the WARN lines from generate.py"),
        ("the sound is muddy/clipping", "drum volumes too high (0.25 is suggested for the hi-hat); too many playsounds on the same tick (limit 255)"),
        ("/reload spams 'objective already exists'", "normal: init adds the objective every time, playback is unaffected"),
        ("garbled playback after /reload while playing", "stale state: just run /function .../play once more"),
    ]:
        print("     %-28s %s" % (sym, cause))

    print("\n" + "=" * 60)
    if problems:
        print("found %d problems (the items marked ✗ above):" % len(problems))
        for p in problems:
            print("  ✗ %s" % p)
        return 1
    print("all checks passed. Type the commands from [6] in game and you are set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
