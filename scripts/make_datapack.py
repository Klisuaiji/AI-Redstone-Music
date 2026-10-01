#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""song.json → a ready-to-install standalone datapack (pack.mcmeta + init + tags + zip).

Step 6 ("standalone mode") of SKILL.md used to rely on hand-written pack.mcmeta/init/tags — exactly
the place where it is easiest to get things wrong (upstream RedstoneMusicBox-v3 shipped pack_format 57
plus a decimal supported_formats 107.1 on 26.2). This script picks the **two generations of pack.mcmeta
syntax** and the directory naming automatically for the target version, ruling out that class of error.

Usage:
    python3 scripts/make_datapack.py song.json -o out/m3-pack --mc-version 26.2
    python3 scripts/make_datapack.py song.json -o out/m3-pack --mc-version 1.20.4 --no-zip

Artifacts:
    out/m3-pack/pack.mcmeta
    out/m3-pack/README.txt
    out/m3-pack/data/<ns>/function/music/<song name>/{play,stop,tick,init,notes/,tree/}
    out/m3-pack/data/<ns>/tags/function/{load,tick}.json         # ≥1.21
    out/m3-pack.zip
Standard library only.
"""
import argparse, json, os, shutil, subprocess, sys, zipfile

try:            # Windows consoles default to GBK: let non-GBK characters (⚠ etc.) degrade to ? instead of raising
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATE = os.path.join(HERE, "generate.py")

# (lowest version, highest version, datapack format) —— from 1.21.9 on this becomes a [major,minor] array
LEGACY_FORMATS = [
    ((1, 13), (1, 14, 4), 4), ((1, 15), (1, 16, 1), 5), ((1, 16, 2), (1, 16, 5), 6),
    ((1, 17), (1, 17), 7), ((1, 18), (1, 18, 1), 8), ((1, 18, 2), (1, 18, 2), 9),
    ((1, 19), (1, 19, 3), 10), ((1, 19, 4), (1, 19, 4), 12), ((1, 20), (1, 20, 1), 15),
    ((1, 20, 2), (1, 20, 2), 18), ((1, 20, 3), (1, 20, 4), 26), ((1, 20, 5), (1, 20, 6), 41),
    ((1, 21), (1, 21, 1), 48), ((1, 21, 2), (1, 21, 3), 57), ((1, 21, 4), (1, 21, 4), 61),
    ((1, 21, 5), (1, 21, 5), 71), ((1, 21, 6), (1, 21, 6), 80), ((1, 21, 7), (1, 21, 8), 81),
]
# ≥1.21.9: the format number is major.minor, and pack.mcmeta must write the two [major,minor] integer
# arrays min_format/max_format
MODERN_FORMATS = [
    ((1, 21, 9), (1, 21, 10), (88, 0)), ((1, 21, 11), (1, 21, 11), (94, 1)),
    ((26, 1), (26, 1), (101, 1)), ((26, 2), (26, 2), (107, 1)), ((26, 3), (26, 3), (121, 0)),
]
RENAME_AT = (1, 21)          # 24w21a: functions/ → function/, tags/functions/ → tags/function/


def vt(v):
    return tuple(int(x) for x in str(v).split("."))


def fmt_cmp(a, b):
    n = max(len(a), len(b))
    return (a + (0,) * (n - len(a))) > (b + (0,) * (n - len(b)))


def resolve_format(ver):
    """version → (syntax, value). syntax = 'legacy' (integer pack_format) or 'modern' ([major,minor] array)."""
    for lo, hi, f in MODERN_FORMATS:
        if not fmt_cmp(lo, ver) and not fmt_cmp(ver, hi):
            return "modern", f
    for lo, hi, f in LEGACY_FORMATS:
        if not fmt_cmp(lo, ver) and not fmt_cmp(ver, hi):
            return "legacy", f
    # version outside the tables: take the nearest entry not above the target, and warn
    known = [(hi, "legacy", f) for lo, hi, f in LEGACY_FORMATS] + \
            [(hi, "modern", f) for lo, hi, f in MODERN_FORMATS]
    below = [k for k in known if not fmt_cmp(k[0], ver)]
    if not below:
        return None, None
    hi, kind, f = max(below, key=lambda k: (len(k[0]), k[0]))
    return kind, f


def w(path, text, crlf=False, bom=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if crlf:
        text = text.replace("\n", "\r\n")
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    with open(path, "wb") as f:
        f.write(data)


def main():
    ap = argparse.ArgumentParser(description="song.json → standalone datapack")
    ap.add_argument("song")
    ap.add_argument("-o", "--out", required=True, help="datapack output directory (pack.mcmeta goes directly inside it)")
    ap.add_argument("--mc-version", default=None, help="target MC version (defaults to meta.mc_version from song.json)")
    ap.add_argument("--speed", type=int, default=None, help="override #speed (defaults to meta.speed)")
    ap.add_argument("--description", default=None, help="description in pack.mcmeta")
    ap.add_argument("--no-zip", action="store_true", help="do not produce a zip")
    ap.add_argument("--keep-helper-files", action="store_true",
                    help="keep the _standalone_*.mcfunction files generate.py produced (merged into init by default)")
    a = ap.parse_args()

    song = json.load(open(a.song, encoding="utf-8"))
    meta = song.get("meta", {})
    ns = meta.get("namespace", "minecraft")
    path = meta.get("path", "music/" + meta.get("name", "song"))
    name = meta.get("name", "song")
    speed = a.speed if a.speed is not None else meta.get("speed", 80)
    ver = a.mc_version or meta.get("mc_version", "1.21")
    song_id = meta.get("song_id", 1)
    kind, fmt = resolve_format(vt(ver))
    if kind is None:
        sys.exit("cannot infer the datapack format for MC %s (see the table in references/datapack.md)" % ver)
    if not fmt_cmp(vt(ver), vt(meta.get("mc_version", ver))):
        pass

    modern = not fmt_cmp(RENAME_AT, vt(ver))          # ver >= 1.21
    fdir = "function" if modern else "functions"
    print("target MC %s → datapack format %s (%s syntax)%s"
          % (ver, fmt if kind == "legacy" else "[%d,%d]" % fmt, kind,
             ", directory is function/" if modern else ", directory is functions/"))
    if kind == "modern" and vt(ver) != vt(meta.get("mc_version", ver)):
        print("  ⚠ song.json has meta.mc_version %s, which does not match --mc-version %s"
              % (meta.get("mc_version"), ver))

    out = os.path.abspath(a.out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    song_dir = os.path.join(out, "data", ns, fdir, path)
    os.makedirs(os.path.dirname(song_dir), exist_ok=True)

    # ---- 1. run generate.py ----
    cmd = [sys.executable, GENERATE, os.path.abspath(a.song), "-o", song_dir, "--speed", str(speed)]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:                                   # write raw bytes so the child's text passes through unchanged
        sys.stdout.buffer.write(r.stdout)
        sys.stdout.buffer.flush()
    except (AttributeError, OSError):
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
    if r.returncode != 0:
        sys.exit("generate.py failed (exit code %d)" % r.returncode)

    # ---- 2. init: rename _standalone_init to its real name ----
    init_src = os.path.join(song_dir, "_standalone_init.mcfunction")
    init_dst = os.path.join(song_dir, "init.mcfunction")
    if os.path.isfile(init_src):
        os.replace(init_src, init_dst)
    elif not os.path.isfile(init_dst):
        w(init_dst, "scoreboard objectives add music_type dummy\n"
                    "scoreboard objectives add nbs_s dummy\n"
                    "scoreboard objectives add nbs_t dummy\n"
                    "scoreboard players set #speed nbs_s %d\n" % speed, crlf=True)
    tick_helper = os.path.join(song_dir, "_standalone_tick.mcfunction")
    if os.path.isfile(tick_helper) and not a.keep_helper_files:
        os.remove(tick_helper)

    # ---- 3. pack.mcmeta (two generations of syntax) ----
    desc = a.description or ("%s redstone music (%s)" % (name, ver))
    if kind == "legacy":
        mcc = ('{\n\t"pack": {\n\t\t"pack_format": %d,\n\t\t"description": %s\n\t}\n}\n'
               % (fmt, json.dumps(desc, ensure_ascii=False)))
    else:
        mcc = ('{\n\t"pack": {\n\t\t"min_format": [%d, %d],\n\t\t"max_format": [%d, %d],\n'
               '\t\t"description": %s\n\t}\n}\n'
               % (fmt[0], fmt[1], fmt[0], fmt[1], json.dumps(desc, ensure_ascii=False)))
    w(os.path.join(out, "pack.mcmeta"), mcc)

    # ---- 4. engine tags ----
    tags_dir = os.path.join(out, "data", "minecraft", "tags", fdir)
    w(os.path.join(tags_dir, "load.json"),
      json.dumps({"replace": False, "values": ["%s:%s/init" % (ns, path)]}, indent=4) + "\n")
    w(os.path.join(tags_dir, "tick.json"),
      json.dumps({"replace": False, "values": ["%s:%s/tick" % (ns, path)]}, indent=4) + "\n")

    # ---- 5. README.txt ----
    w(os.path.join(out, "README.txt"),
      "================ %s redstone music datapack ================\n"
      "Target version: Minecraft Java %s (datapack format %s)\n"
      "Playback path: %s:%s     song_id = %s     #speed nbs_s = %d\n"
      "\n"
      "[Install]\n"
      "1. Put %s.zip (or the extracted folder) into the world's datapacks/\n"
      "2. Run /reload in game\n"
      "3. /function %s:%s/play   start playback\n"
      "   /function %s:%s/stop   stop\n"
      "   Give yourself the no_music tag = mute this song (does not affect other players)\n"
      "\n"
      "[Attach to an existing lemon-family music datapack]\n"
      "  Delete pack.mcmeta and data/minecraft/tags/%s/{load,tick}.json,\n"
      "  put data/%s/%s/%s/ into the host pack, make sure the host runs %s:%s/tick every tick,\n"
      "  and that init sets #speed nbs_s = %d; if song_id collides, change the number in play/stop/tick.\n"
      "\n"
      "[Generation info]\n"
      "  song.json: %s\n"
      "  generator: scripts/generate.py from Klisuaiji/RedstoneMusic-Skill\n"
      % (name, ver, fmt if kind == "legacy" else "[%d,%d]" % fmt, ns, path, song_id, speed,
         name, ns, path, ns, path, fdir, ns, fdir, path, ns, path, speed,
         os.path.basename(a.song)), bom=True)

    # ---- 6. zip ----
    zpath = out + ".zip"
    if not a.no_zip:
        if os.path.isfile(zpath):
            os.remove(zpath)
        n = 0
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for dp, _, fs in os.walk(out):
                for fn in sorted(fs):
                    full = os.path.join(dp, fn)
                    z.write(full, os.path.relpath(full, out).replace(os.sep, "/"))
                    n += 1
        print("zip: %s (%d files, %.2f MB)" % (zpath, n, os.path.getsize(zpath) / 1e6))
    nfiles = sum(len(fs) for _, _, fs in os.walk(out))
    print("datapack: %s (%d files)" % (out, nfiles))
    print("play: /function %s:%s/play" % (ns, path))
    print("self-check: python3 scripts/validate_pack.py --pack %s --namespace %s --song %s --song-id %s --speed %d --mc-version %s"
          % (out, ns, name, song_id, speed, ver))


if __name__ == "__main__":
    main()
