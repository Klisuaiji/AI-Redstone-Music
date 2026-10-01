#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end smoke test (standard library only, can be used directly as CI):

    python3 tests/smoke_test.py

Covers:
  1. song.json → generate.py → validate_pack.py all green, and every notes file is referenced
     exactly once by tree
  2. **Regression test**: revert tree to the upstream 2-cell-wide leaves → validate_pack.py must
     fail (this is the historical "the second note on adjacent ticks is silent forever" bug, and
     someone must keep watching it)
  3. make_datapack.py: 26.2 emits min_format/max_format, 1.20.4 emits pack_format + functions/ dir
  4. when pack.mcmeta is written the wrong way validate_pack.py must fail (writing only
     pack_format for 26.2 is wrong)
"""
import json, os, re, shutil, subprocess, sys, uuid, zipfile

try:            # when the console is GBK, non-GBK characters degrade to ?, so the test must not crash on print
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
S = os.path.join(ROOT, "scripts")
PY = sys.executable

results = []


def run(cmd):
    # Subprocesses always use UTF-8 output (otherwise on Windows they write to the pipe as GBK and
    # reading it back turns into mojibake), so assertions can rely on that text directly.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))


def make_song(path, name="demo", song_id=7):
    """Deliberately make ticks 0/1/2 all adjacent — upstream 2-cell-wide leaves eat one note here."""
    song = {"meta": {"name": name, "namespace": "minecraft", "path": "music/" + name,
                     "song_id": song_id, "mc_version": "26.2", "style": "standalone",
                     "time_unit": "nbs_s_units", "speed": 80, "auto_stop": True,
                     "next_song": None, "mute_tag": "no_music"},
            "tracks": [
                {"name": "lead", "include": True, "instrument_default": "harp", "notes": [
                    {"t": 0, "midi": 66}, {"t": 1, "midi": 68}, {"t": 2, "midi": 69},
                    {"t": 5, "midi": 71}, {"t": 12, "midi": 73}]},
                {"name": "bass", "include": True, "instrument_default": "bass", "notes": [
                    {"t": 0, "midi": 42}, {"t": 5, "midi": 40}, {"t": 12, "midi": 38}]},
                {"name": "drums", "include": True, "instrument_default": "basedrum", "notes": [
                    {"t": 0, "midi": 54, "inst": "basedrum", "vol": 0.6},
                    {"t": 2, "midi": 54, "inst": "hat", "vol": 0.25},
                    {"t": 5, "midi": 54, "inst": "snare", "vol": 0.5}]},
            ]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(song, f, ensure_ascii=False)
    return song


def tree_refs(song_dir):
    """How many times each notes/<t> is referenced inside tree."""
    ref = {}
    tdir = os.path.join(song_dir, "tree")
    for fn in os.listdir(tdir):
        txt = open(os.path.join(tdir, fn), encoding="utf-8").read()
        for m in re.finditer(r"/notes/(\d+)", txt):
            t = int(m.group(1))
            ref[t] = ref.get(t, 0) + 1
    return ref


def main():
    # By default the temporary work area is created under the repo directory (some sandbox
    # environments do not allow writing to the system temp) and it is removed automatically after
    # the run. Do not use tempfile.mkdtemp: it creates the directory with 0700, and in some Windows
    # sandboxes the ACL then blocks subsequent writes.
    base = os.environ.get("RSM_SMOKE_DIR") or ROOT
    tmp = os.path.join(base, ".rsm-smoke-" + uuid.uuid4().hex[:8])
    os.makedirs(tmp)
    print("work dir: %s\n" % tmp)
    try:
        songp = os.path.join(tmp, "demo.song.json")
        make_song(songp)
        out = os.path.join(tmp, "out")

        # ---------- 1. generate + validate ----------
        print("[1] generate.py → validate_pack.py")
        code, log = run([PY, os.path.join(S, "generate.py"), songp, "-o", os.path.join(out, "music", "demo")])
        check("generate.py exit code 0", code == 0, log.strip()[-200:])
        song_dir = os.path.join(out, "music", "demo")
        check("both notes/ and tree/ are generated",
              os.path.isdir(os.path.join(song_dir, "notes")) and os.path.isdir(os.path.join(song_dir, "tree")))

        notes = sorted(int(f[:-11]) for f in os.listdir(os.path.join(song_dir, "notes")))
        ref = tree_refs(song_dir)
        bad = [t for t in notes if ref.get(t, 0) != 1]
        check("every notes file is referenced exactly once by tree (including adjacent ticks 0/1/2)",
              not bad, "unexpected: %s" % bad)

        code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", out,
                         "--namespace", "minecraft", "--song", "demo", "--song-id", "7", "--speed", "80",
                         "--mc-version", "26.2"])
        check("validate_pack.py passes all checks", code == 0, log.strip()[-300:])
        check("validation ran the tree state-machine simulation",
              "state-machine" in log or "ALL CHECKS PASSED" in log)

        # ---------- 2. regression: 2-cell-wide leaves must be caught ----------
        print("\n[2] regression test: revert tree to 2-cell-wide leaves (the historical silent bug)")
        bug = os.path.join(tmp, "buggy")
        shutil.copytree(out, bug)
        bdir = os.path.join(bug, "music", "demo", "tree")
        for f in os.listdir(bdir):
            os.remove(os.path.join(bdir, f))
        # replicate the upstream algorithm: range width 2, and only rng[0] is fired
        open(os.path.join(bdir, "0_1.mcfunction"), "w", encoding="utf-8", newline="").write(
            "execute if score music_progress nbs_s matches 0..240 "
            "if score music_progress nbs_t matches ..-1 run function minecraft:music/demo/notes/0\r\n")
        open(os.path.join(bdir, "2_3.mcfunction"), "w", encoding="utf-8", newline="").write(
            "execute if score music_progress nbs_s matches 160..400 "
            "if score music_progress nbs_t matches ..1 run function minecraft:music/demo/notes/2\r\n")
        open(os.path.join(bdir, "4_7.mcfunction"), "w", encoding="utf-8", newline="").write(
            "execute if score music_progress nbs_s matches 320..720 "
            "if score music_progress nbs_t matches ..4 run function minecraft:music/demo/notes/5\r\n")
        open(os.path.join(bdir, "8_15.mcfunction"), "w", encoding="utf-8", newline="").write(
            "execute if score music_progress nbs_s matches 640..1360 "
            "if score music_progress nbs_t matches ..11 run function minecraft:music/demo/notes/12\r\n")
        open(os.path.join(bdir, "0_15.mcfunction"), "w", encoding="utf-8", newline="").write(
            "execute if score music_progress nbs_s matches 0..680 run function minecraft:music/demo/tree/0_1\r\n"
            "execute if score music_progress nbs_s matches 160..880 run function minecraft:music/demo/tree/2_3\r\n"
            "execute if score music_progress nbs_s matches 320..1200 run function minecraft:music/demo/tree/4_7\r\n"
            "execute if score music_progress nbs_s matches 640..1840 run function minecraft:music/demo/tree/8_15\r\n")
        code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", bug,
                         "--namespace", "minecraft", "--song", "demo", "--song-id", "7", "--speed", "80"])
        check("2-cell-wide leaves are judged FAIL", code != 0)
        check("the error names notes/1 as silent", "notes/1" in log or "silent" in log, log.strip()[-300:])

        # ---------- 3. make_datapack: two generations of pack.mcmeta ----------
        print("\n[3] make_datapack.py")
        p26 = os.path.join(tmp, "pack26")
        code, log = run([PY, os.path.join(S, "make_datapack.py"), songp, "-o", p26, "--mc-version", "26.2"])
        check("make_datapack.py (26.2) exit code 0", code == 0, log.strip()[-300:])
        mc = json.load(open(os.path.join(p26, "pack.mcmeta"), encoding="utf-8"))["pack"]
        check("26.2 uses min_format/max_format = [107,1]",
              mc.get("min_format") == [107, 1] and mc.get("max_format") == [107, 1], str(mc))
        check("26.2 has no pack_format/supported_formats",
              "pack_format" not in mc and "supported_formats" not in mc)
        check("26.2 uses function/ and tags/function/ directories",
              os.path.isdir(os.path.join(p26, "data", "minecraft", "function", "music", "demo")) and
              os.path.isfile(os.path.join(p26, "data", "minecraft", "tags", "function", "tick.json")))
        z = os.path.join(tmp, "pack26.zip")
        check("a zip was produced and pack.mcmeta sits at the zip root",
              os.path.isfile(z) and "pack.mcmeta" in zipfile.ZipFile(z).namelist())
        code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", p26, "--namespace", "minecraft",
                         "--song", "demo", "--song-id", "7", "--speed", "80", "--mc-version", "26.2"])
        check("the built 26.2 datapack passes validation", code == 0, log.strip()[-300:])

        p120 = os.path.join(tmp, "pack1204")
        code, log = run([PY, os.path.join(S, "make_datapack.py"), songp, "-o", p120,
                         "--mc-version", "1.20.4", "--no-zip"])
        mc = json.load(open(os.path.join(p120, "pack.mcmeta"), encoding="utf-8"))["pack"]
        check("1.20.4 uses pack_format = 26", mc.get("pack_format") == 26, str(mc))
        check("1.20.4 uses functions/ and tags/functions/ directories",
              os.path.isdir(os.path.join(p120, "data", "minecraft", "functions", "music", "demo")) and
              os.path.isfile(os.path.join(p120, "data", "minecraft", "tags", "functions", "tick.json")))

        # ---------- 4. a wrongly written pack.mcmeta must be rejected ----------
        print("\n[4] pack.mcmeta syntax validation")
        bad = os.path.join(tmp, "badmeta")
        shutil.copytree(p26, bad)
        with open(os.path.join(bad, "pack.mcmeta"), "w", encoding="utf-8") as f:
            json.dump({"pack": {"pack_format": 107, "description": "wrong"}}, f)
        code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", bad, "--namespace", "minecraft",
                         "--song", "demo", "--song-id", "7", "--speed", "80", "--mc-version", "26.2"])
        check("26.2 with only pack_format is judged FAIL", code != 0, log.strip()[-200:])

        # ---------- 5. a real MIDI through the whole thing (examples/demo.mid) ----------
        print("\n[5] example MIDI end-to-end (scan → midi_to_song → make_datapack → validate)")
        mid = os.path.join(ROOT, "examples", "demo.mid")
        if not os.path.isfile(mid):
            check("examples/demo.mid exists", False, "run python3 tests/gen_demo_midi.py examples/demo.mid first")
        else:
            code, log = run([PY, os.path.join(S, "scan_midi.py"), mid])
            check("scan_midi.py runs and gives a verdict", code == 0 and "verdict" in log.lower(), log.strip()[-200:])
            song2p = os.path.join(tmp, "demo2.song.json")
            code, log = run([PY, os.path.join(S, "midi_to_song.py"), mid, "-o", song2p,
                             "--name", "demo", "--song-id", "8", "--mc-version", "26.2"])
            check("midi_to_song.py runs", code == 0, log.strip()[-200:])
            song2 = json.load(open(song2p, encoding="utf-8"))
            n2 = sum(len(t["notes"]) for t in song2["tracks"])
            check("the produced song.json has notes (%d)" % n2, n2 > 100)
            ticks2 = sorted({n["t"] for t in song2["tracks"] for n in t["notes"]})
            adj2 = [b for a, b in zip(ticks2, ticks2[1:]) if b - a == 1]
            check("the example MIDI produces adjacent note ticks (%d pairs, exactly the silent bug scenario)" % len(adj2), len(adj2) > 0)
            p2 = os.path.join(tmp, "demo-pack")
            code, log = run([PY, os.path.join(S, "make_datapack.py"), song2p, "-o", p2,
                             "--mc-version", "26.2", "--no-zip"])
            check("make_datapack.py handles the real MIDI output", code == 0, log.strip()[-200:])
            code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", p2, "--namespace", "minecraft",
                             "--song", "demo", "--song-id", "8", "--speed", "80", "--mc-version", "26.2"])
            check("that datapack passes validation", code == 0, log.strip()[-300:])
            code, log = run([PY, os.path.join(S, "doctor.py"), "--pack", p2, "--mc-version", "26.2",
                             "--song", "demo", "--song-id", "8", "--speed", "80"])
            check("doctor.py all [OK]", code == 0 and "[X]" not in log, log.strip()[-200:])
            code, log = run([PY, os.path.join(S, "midi_to_song.py"), mid, "-o", os.path.join(tmp, "tr80.json"),
                             "--name", "demo", "--song-id", "8", "--tick-rate", "80"])
            check("--tick-rate 80 works (grid 12.5ms)", code == 0 and "12.50 ms" in log, log.strip()[-200:])

        # ---------- 6. music box: register a song → static checks ----------
        print("\n[6] music box (generic framework + registered song)")
        box_src = os.path.join(ROOT, "examples", "musicbox", "datapack")
        if not os.path.isdir(box_src):
            check("examples/musicbox/datapack exists", False, "the music box framework is missing")
        else:
            code, log = run([PY, os.path.join(S, "check_refs.py"), box_src])
            check("all function references of the empty box resolve", code == 0, log.strip()[-200:])
            box = os.path.join(tmp, "box")
            shutil.copytree(box_src, box)
            lrc = os.path.join(tmp, "t.lrc")
            with open(lrc, "w", encoding="utf-8") as f:
                f.write("[00:00.00]first line\n[00:02.50]second line\n")
            code, log = run([PY, os.path.join(S, "add_to_musicbox.py"), "--box", box,
                             "--song", mid, "--name", "Smoke Test Song", "--lrc", lrc])
            check("add_to_musicbox.py registers MIDI + lyrics", code == 0, log.strip()[-200:])
            code, log = run([PY, os.path.join(S, "check_refs.py"), box])
            check("all references still resolve after registration", code == 0, log.strip()[-200:])
            mx = open(os.path.join(box, "data/rmb/function/song/max.mcfunction"), encoding="utf-8").read()
            check("#max is written as 1", "#max mb_cfg 1" in mx, mx.strip()[-120:])
            songdir = os.path.join(box, "data/rmb/function/song/1")
            check("the song quartet is complete (play/tick/stop/lrc)",
                  all(os.path.isfile(os.path.join(songdir, f)) for f in
                      ("play.mcfunction", "tick.mcfunction", "stop.mcfunction", "lrc.mcfunction")))
            lrcf = open(os.path.join(songdir, "lrc.mcfunction"), encoding="utf-8").read()
            check("lyrics sorted by nbs_s (2.5s → 50 ticks → 4000)", "4000.." in lrcf, lrcf.strip()[-160:])
            menu = open(os.path.join(box, "data/rmb/function/box/menu_list.mcfunction"), encoding="utf-8").read()
            check("the menu shows a clickable song name", "/trigger play set 1" in menu and "Smoke Test Song" in menu)
            code, log = run([PY, os.path.join(S, "add_to_musicbox.py"), "--box", box,
                             "--song", mid, "--name", "Second"])
            check("the second id is allocated automatically", code == 0 and "[2]" in log, log.strip()[-160:])
            code, log = run([PY, os.path.join(S, "add_to_musicbox.py"), "--box", box, "--remove", "1"])
            check("a song can be removed", code == 0, log.strip()[-160:])
            code, log = run([PY, os.path.join(S, "check_refs.py"), box])
            check("all references still resolve after removal", code == 0, log.strip()[-200:])
            code, log = run([PY, os.path.join(S, "add_to_musicbox.py"), "--box", box,
                             "--song", mid, "--name", "dup", "--id", "2"])
            check("an id conflict is rejected", code != 0)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    nfail = sum(1 for _, ok, _ in results if not ok)
    print("\n%d checks, %d failed" % (len(results), nfail))
    if nfail:
        for name, _, detail in results:
            if not _:
                print("  FAIL: %s\n        %s" % (name, detail))
        return 1
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
