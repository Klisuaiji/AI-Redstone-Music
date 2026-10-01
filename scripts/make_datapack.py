#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""song.json → 可直接安装的独立数据包（pack.mcmeta + init + tags + zip）。

SKILL.md 第六步的"独立模式"过去靠手写 pack.mcmeta/init/tags —— 这正是最容易写错的地方
（上游 RedstoneMusicBox-v3 就在 26.2 上写成了 pack_format 57 + supported_formats 小数 107.1）。
这个脚本按目标版本自动选**两代 pack.mcmeta 写法**与目录命名，杜绝这类错误。

用法：
    python3 scripts/make_datapack.py song.json -o out/m3-pack --mc-version 26.2
    python3 scripts/make_datapack.py song.json -o out/m3-pack --mc-version 1.20.4 --no-zip

产物：
    out/m3-pack/pack.mcmeta
    out/m3-pack/README.txt
    out/m3-pack/data/<ns>/function/music/<歌名>/{play,stop,tick,init,notes/,tree/}
    out/m3-pack/data/<ns>/tags/function/{load,tick}.json         # ≥1.21
    out/m3-pack.zip
仅用标准库。
"""
import argparse, json, os, shutil, subprocess, sys, zipfile

try:            # Windows 控制台默认 GBK：让非 GBK 字符（⚠ 等）降级为 ?，而不是直接抛异常
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATE = os.path.join(HERE, "generate.py")

# (最低版本, 最高版本, 数据包格式) —— 1.21.9 起改用 [主,次] 数组
LEGACY_FORMATS = [
    ((1, 13), (1, 14, 4), 4), ((1, 15), (1, 16, 1), 5), ((1, 16, 2), (1, 16, 5), 6),
    ((1, 17), (1, 17), 7), ((1, 18), (1, 18, 1), 8), ((1, 18, 2), (1, 18, 2), 9),
    ((1, 19), (1, 19, 3), 10), ((1, 19, 4), (1, 19, 4), 12), ((1, 20), (1, 20, 1), 15),
    ((1, 20, 2), (1, 20, 2), 18), ((1, 20, 3), (1, 20, 4), 26), ((1, 20, 5), (1, 20, 6), 41),
    ((1, 21), (1, 21, 1), 48), ((1, 21, 2), (1, 21, 3), 57), ((1, 21, 4), (1, 21, 4), 61),
    ((1, 21, 5), (1, 21, 5), 71), ((1, 21, 6), (1, 21, 6), 80), ((1, 21, 7), (1, 21, 8), 81),
]
# ≥1.21.9：格式号是 主.次，pack.mcmeta 必须写 min_format/max_format 两个 [主,次] 整数数组
MODERN_FORMATS = [
    ((1, 21, 9), (1, 21, 10), (88, 0)), ((1, 21, 11), (1, 21, 11), (94, 1)),
    ((26, 1), (26, 1), (101, 1)), ((26, 2), (26, 2), (107, 1)), ((26, 3), (26, 3), (121, 0)),
]
RENAME_AT = (1, 21)          # 24w21a：functions/ → function/、tags/functions/ → tags/function/


def vt(v):
    return tuple(int(x) for x in str(v).split("."))


def fmt_cmp(a, b):
    n = max(len(a), len(b))
    return (a + (0,) * (n - len(a))) > (b + (0,) * (n - len(b)))


def resolve_format(ver):
    """版本 → (写法, 值)。写法 = 'legacy'（pack_format 整数）或 'modern'（[主,次] 数组）。"""
    for lo, hi, f in MODERN_FORMATS:
        if not fmt_cmp(lo, ver) and not fmt_cmp(ver, hi):
            return "modern", f
    for lo, hi, f in LEGACY_FORMATS:
        if not fmt_cmp(lo, ver) and not fmt_cmp(ver, hi):
            return "legacy", f
    # 表外版本：取不大于目标的最近一项，并提示
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
    ap = argparse.ArgumentParser(description="song.json → 独立数据包")
    ap.add_argument("song")
    ap.add_argument("-o", "--out", required=True, help="数据包输出目录（该目录内直接放 pack.mcmeta）")
    ap.add_argument("--mc-version", default=None, help="目标 MC 版本（默认取 song.json 的 meta.mc_version）")
    ap.add_argument("--speed", type=int, default=None, help="覆盖 #speed（默认取 meta.speed）")
    ap.add_argument("--description", default=None, help="pack.mcmeta 里的描述")
    ap.add_argument("--no-zip", action="store_true", help="不生成 zip")
    ap.add_argument("--keep-helper-files", action="store_true",
                    help="保留 generate.py 生成的 _standalone_*.mcfunction（默认合并进 init）")
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
        sys.exit("无法为 MC %s 推断数据包格式（对照表见 references/datapack.md）" % ver)
    if not fmt_cmp(vt(ver), vt(meta.get("mc_version", ver))):
        pass

    modern = not fmt_cmp(RENAME_AT, vt(ver))          # ver >= 1.21
    fdir = "function" if modern else "functions"
    print("目标 MC %s → 数据包格式 %s（%s 写法）%s"
          % (ver, fmt if kind == "legacy" else "[%d,%d]" % fmt, kind,
             "，目录用 function/" if modern else "，目录用 functions/"))
    if kind == "modern" and vt(ver) != vt(meta.get("mc_version", ver)):
        print("  ⚠ song.json 的 meta.mc_version 是 %s，与 --mc-version %s 不一致"
              % (meta.get("mc_version"), ver))

    out = os.path.abspath(a.out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    song_dir = os.path.join(out, "data", ns, fdir, path)
    os.makedirs(os.path.dirname(song_dir), exist_ok=True)

    # ---- 1. 跑 generate.py ----
    cmd = [sys.executable, GENERATE, os.path.abspath(a.song), "-o", song_dir, "--speed", str(speed)]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:                                   # 直接写字节：Windows 控制台是 GBK 时中文也能透传
        sys.stdout.buffer.write(r.stdout)
        sys.stdout.buffer.flush()
    except (AttributeError, OSError):
        sys.stdout.write(r.stdout.decode("utf-8", "replace"))
    if r.returncode != 0:
        sys.exit("generate.py 失败（退出码 %d）" % r.returncode)

    # ---- 2. init：把 _standalone_init 换成正式名字 ----
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

    # ---- 3. pack.mcmeta（两代写法） ----
    desc = a.description or ("%s 红石音乐 (%s)" % (name, ver))
    if kind == "legacy":
        mcc = ('{\n\t"pack": {\n\t\t"pack_format": %d,\n\t\t"description": %s\n\t}\n}\n'
               % (fmt, json.dumps(desc, ensure_ascii=False)))
    else:
        mcc = ('{\n\t"pack": {\n\t\t"min_format": [%d, %d],\n\t\t"max_format": [%d, %d],\n'
               '\t\t"description": %s\n\t}\n}\n'
               % (fmt[0], fmt[1], fmt[0], fmt[1], json.dumps(desc, ensure_ascii=False)))
    w(os.path.join(out, "pack.mcmeta"), mcc)

    # ---- 4. 引擎标签 ----
    tags_dir = os.path.join(out, "data", "minecraft", "tags", fdir)
    w(os.path.join(tags_dir, "load.json"),
      json.dumps({"replace": False, "values": ["%s:%s/init" % (ns, path)]}, indent=4) + "\n")
    w(os.path.join(tags_dir, "tick.json"),
      json.dumps({"replace": False, "values": ["%s:%s/tick" % (ns, path)]}, indent=4) + "\n")

    # ---- 5. README.txt ----
    w(os.path.join(out, "README.txt"),
      "================ %s 红石音乐数据包 ================\n"
      "目标版本: Minecraft Java %s（数据包格式 %s）\n"
      "播放路径: %s:%s     song_id = %s     #speed nbs_s = %d\n"
      "\n"
      "【安装】\n"
      "1. 把 %s.zip（或解压出的文件夹）放进存档的 datapacks/\n"
      "2. 进游戏执行 /reload\n"
      "3. /function %s:%s/play   开始播放\n"
      "   /function %s:%s/stop   停止\n"
      "   给自己打 no_music 标签 = 本曲静音（不影响其他玩家）\n"
      "\n"
      "【挂到已有的 lemon 系音乐数据包】\n"
      "  删除 pack.mcmeta、data/minecraft/tags/%s/{load,tick}.json，\n"
      "  把 data/%s/%s/%s/ 放进宿主包，确认宿主每刻执行 %s:%s/tick、\n"
      "  init 里 #speed nbs_s = %d；若 song_id 冲突，改 play/stop/tick 三处数字。\n"
      "\n"
      "【生成信息】\n"
      "  song.json: %s\n"
      "  生成器: Klisuaiji/RedstoneMusic-Skill 的 scripts/generate.py\n"
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
        print("zip: %s（%d 个文件，%.2f MB）" % (zpath, n, os.path.getsize(zpath) / 1e6))
    nfiles = sum(len(fs) for _, _, fs in os.walk(out))
    print("数据包: %s（%d 个文件）" % (out, nfiles))
    print("播放: /function %s:%s/play" % (ns, path))
    print("自检: python3 scripts/validate_pack.py --pack %s --namespace %s --song %s --song-id %s --speed %d --mc-version %s"
          % (out, ns, name, song_id, speed, ver))


if __name__ == "__main__":
    main()
