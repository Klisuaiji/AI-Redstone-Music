#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic static check for a datapack (does not need Minecraft running).

Division of labour with `validate_pack.py`: `validate_pack.py` only understands the **song datapacks**
this workflow generates (it checks tree/notes/timeline), while `check_refs.py` accepts **any** datapack
and does the basic health check that you did not break the pack while editing:

  * does every .mcfunction referenced by `function <namespace>:<path>` really exist
    (the easiest mistake to make, and one that only errors inside the game)
  * is every `data/**/*.json` valid JSON
  * do all `.mcfunction` files use CRLF line endings (common after editing in Windows notepad)
  * which functions use macros (lines starting with `$`); those need to be called with
    `with storage/entity/block` or `/function <name> {data}`

Usage:
    python3 scripts/check_refs.py <datapack root>
    python3 scripts/check_refs.py examples/musicbox/datapack

Exit code 0 if everything passes, otherwise 1. Standard library only.
"""
import json, os, re, sys

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

FN_RE = re.compile(r"(?:^|[\s\[])(?:run )?function ([a-z0-9_.-]+):([a-z0-9_./-]+)")


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: check_refs.py <datapack root>")
    root = sys.argv[1]
    if not os.path.isfile(os.path.join(root, "pack.mcmeta")):
        print("note: %s has no pack.mcmeta — still checking references" % root)

    missing, macros, badjson, badcrlf = [], [], [], []
    files = set()
    for dp, _, fs in os.walk(root):
        for f in fs:
            files.add(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))

    for rel in sorted(files):
        p = os.path.join(root, rel)
        if rel.endswith(".json"):
            try:
                json.load(open(p, encoding="utf-8"))
            except Exception as e:
                badjson.append("%s: %s" % (rel, e))
        if not rel.endswith(".mcfunction"):
            continue
        raw = open(p, "rb").read()
        if b"\n" in raw and b"\r\n" not in raw:
            badcrlf.append(rel)
        text = raw.decode("utf-8", "replace")
        for m in FN_RE.finditer(text):
            if "data/%s/function/%s.mcfunction" % (m.group(1), m.group(2)) not in files:
                missing.append("%s → %s:%s" % (rel, m.group(1), m.group(2)))
        if any(l.startswith("$") for l in text.splitlines()):
            macros.append(rel)

    n_mc = sum(1 for f in files if f.endswith(".mcfunction"))
    print("total files: %d (%d mcfunction)" % (len(files), n_mc))
    print("macro functions (with $ lines): %s" % (", ".join(sorted(macros)) or "none"))

    ok = True
    if missing:
        ok = False
        print("\n[FAIL] %d references to functions that do not exist:" % len(missing))
        for m in missing[:30]:
            print("   ", m)
    if badjson:
        ok = False
        print("\n[FAIL] invalid JSON:")
        for m in badjson:
            print("   ", m)
    if badcrlf:
        ok = False
        print("\n[FAIL] mcfunction with non-CRLF line endings: %s" % ", ".join(badcrlf))
    if ok:
        print("\nOK: every function reference resolves, JSON is valid, line endings are correct")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
