#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据包通用静态检查（不需要启动 Minecraft）。

和 `validate_pack.py` 的分工：`validate_pack.py` 只认本工作流生成的**歌曲数据包**（检查树/音符/时轴），
`check_refs.py` 认**任何**数据包，做的是"改完别把包改坏"的基础体检：

  * 每个 `function <命名空间>:<路径>` 引用的 .mcfunction 是否真的存在（最容易犯、且只在游戏里报错的错）
  * `data/**/*.json` 是否都是合法 JSON
  * `.mcfunction` 是否都是 CRLF 行尾（Windows 记事本改过之后常见）
  * 提示哪些函数用了宏（`$` 开头），它们需要 `with storage/entity/block` 或 `/function <名> {数据}` 调用

用法：
    python3 scripts/check_refs.py <数据包根目录>
    python3 scripts/check_refs.py examples/musicbox/datapack

全部通过退出码 0，否则 1。仅用标准库。
"""
import json, os, re, sys

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

FN_RE = re.compile(r"(?:^|[\s\[])(?:run )?function ([a-z0-9_.-]+):([a-z0-9_./-]+)")


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: check_refs.py <数据包根目录>")
    root = sys.argv[1]
    if not os.path.isfile(os.path.join(root, "pack.mcmeta")):
        print("提示: %s 里没有 pack.mcmeta —— 仍在继续检查引用" % root)

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
    print("文件总数: %d（其中 mcfunction %d）" % (len(files), n_mc))
    print("宏函数（含 $ 行）: %s" % (", ".join(sorted(macros)) or "无"))

    ok = True
    if missing:
        ok = False
        print("\n[FAIL] 引用了不存在的函数 %d 处:" % len(missing))
        for m in missing[:30]:
            print("   ", m)
    if badjson:
        ok = False
        print("\n[FAIL] JSON 不合法:")
        for m in badjson:
            print("   ", m)
    if badcrlf:
        ok = False
        print("\n[FAIL] 非 CRLF 行尾的 mcfunction: %s" % ", ".join(badcrlf))
    if ok:
        print("\nOK: 所有函数引用都能解析，JSON 合法，行尾正确")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
