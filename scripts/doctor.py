#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""红石音乐数据包体检 / "怎么没声音" 一键排查。

跟 validate_pack.py 的分工：validate_pack.py 是**交付前的硬门禁**（CI 用，任何一条不过就退出码 1）；
doctor.py 是**面向人的排查向导**——逐项打印 ✓/✗ 并在每个 ✗ 下面给"怎么修"，
最后附「进游戏按顺序敲什么」和「症状 → 原因」速查表。它内部会调用 validate_pack.py 做深度检查。

用法：
    python3 scripts/doctor.py --pack out/m3                      # 体检一个数据包目录
    python3 scripts/doctor.py --pack m3-redstone-music-26.2.zip  # 直接体检 zip（只做结构检查）
    python3 scripts/doctor.py --pack out/m3 --mc-version 26.2 --song m3 --song-id 9 --speed 80
    python3 scripts/doctor.py --pack out/m3 --world-dir "<存档>/datapacks"   # 顺带确认装没装进世界
仅用标准库。
"""
import argparse, json, os, subprocess, sys, zipfile

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATE = os.path.join(HERE, "validate_pack.py")
# GBK 控制台无法区分 ✓/✗（都会被替换成 ?），这时退回 ASCII 标记，保证一眼能看出好坏
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
    """把"目录"和"zip"统一成同一套读接口。"""

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
    ap = argparse.ArgumentParser(description="红石音乐数据包体检 / 没声音排查")
    ap.add_argument("--pack", required=True, help="数据包目录或 zip")
    ap.add_argument("--mc-version", default=None, help="目标 MC 版本（不填则只做通用检查）")
    ap.add_argument("--namespace", default="minecraft")
    ap.add_argument("--path", default=None, help="函数路径，默认 music/<song>")
    ap.add_argument("--song", default=None)
    ap.add_argument("--song-id", type=int, default=None)
    ap.add_argument("--speed", type=int, default=80)
    ap.add_argument("--world-dir", default=None, help="存档的 datapacks 目录，用来确认装没装进世界")
    a = ap.parse_args()
    if not a.song:
        a.song = os.path.splitext(os.path.basename(os.path.normpath(a.pack)))[0]
    path = a.path or ("music/" + a.song)
    full = "%s:%s" % (a.namespace, path)

    print("=== 红石音乐数据包体检：%s ===" % a.pack)
    print("    目标版本 %s | 命名空间 %s | 路径 %s | song_id %s | #speed %s\n"
          % (a.mc_version or "(未指定)", a.namespace, path, a.song_id, a.speed))

    src = Src(a.pack)
    if src.zip:
        print("[0] 输入是 zip —— 只做结构与元数据检查；深度检查请先解压后再跑一次")
        print("     zip 根目录必须是 pack.mcmeta（很多压缩工具会多套一层文件夹）")

    # ---------- 1. 结构 ----------
    print("\n[1] 文件结构")
    item(src.has("pack.mcmeta"), "pack.mcmeta 在数据包根目录",
         "把 zip 解开看是不是多套了一层文件夹；数据包根目录必须直接放 pack.mcmeta")
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
    item(fdir is not None, "歌曲目录存在（data/%s/<%s>/%s/）" % (a.namespace, "function" if modern is not False else "functions", path),
         "确认 --song/--path 与 generate.py 的 -o 目录一致；1.21 起目录是单数 function/，≤1.20.4 是复数 functions/")
    if fdir:
        for f in ("play", "stop", "tick"):
            item(src.has("data/%s/%s/%s/%s.mcfunction" % (a.namespace, fdir, path, f)),
                 "%s.mcfunction 存在" % f, "用 generate.py 重新生成")
        if src.zip:
            n_notes = sum(1 for x in src.names if x.endswith(".mcfunction") and
                          x.startswith("data/%s/%s/%s/notes/" % (a.namespace, fdir, path)))
        else:
            nd = os.path.join(a.pack, "data", a.namespace, fdir, path, "notes")
            n_notes = len([x for x in os.listdir(nd) if x.endswith(".mcfunction")])
        item(n_notes > 0, "notes/ 有 %d 个文件" % n_notes, "notes/ 为空：song.json 里没有音符，或 generate.py 没跑到写文件")

    # ---------- 2. pack.mcmeta 与版本 ----------
    print("\n[2] pack.mcmeta 与目标版本")
    if src.has("pack.mcmeta"):
        try:
            pk = json.loads(src.read("pack.mcmeta"))["pack"]
        except Exception as e:
            pk = None
            item(False, "pack.mcmeta 是合法 JSON", "常见的坑：多余的逗号、中文引号、BOM。用 json 校验一下: %s" % e)
        if pk is not None:
            has_new = "min_format" in pk or "max_format" in pk
            has_old = "pack_format" in pk
            if a.mc_version and modern:
                item(has_new and not has_old, "≥1.21.9 用 min_format/max_format 且不写 pack_format",
                     "≥1.21.9（数据包格式 ≥82）必须写成 {\"pack\":{\"min_format\":[107,1],"
                     "\"max_format\":[107,1],\"description\":\"...\"}}；仍写 pack_format 会被判不兼容。"
                     "直接用 make_datapack.py 生成可避免")
                if has_new:
                    ok_fmt = all(isinstance(pk.get(k), list) and len(pk[k]) == 2 and
                                 all(isinstance(y, int) for y in pk[k]) for k in ("min_format", "max_format"))
                    item(ok_fmt, "format 是 [主,次] 两个整数（没写小数 107.1）",
                         "不能写 107.1 这种小数，要写 [107, 1]")
            else:
                item(has_old and not has_new, "≤1.21.8 用 pack_format",
                     "≤1.21.8 用 \"pack_format\": <数字>；min_format/max_format 是 1.21.9+ 的写法")
            print("     （内容: %s）" % json.dumps(pk, ensure_ascii=False)[:150])

    # ---------- 3. 标签 / init / song_id ----------
    print("\n[3] 引擎标签、init 与 song_id")
    tag_dir = "data/minecraft/tags/%s" % (fdir or "function")
    has_tags = src.has(tag_dir + "/tick.json") and src.has(tag_dir + "/load.json")
    item(has_tags, "load.json / tick.json 存在（独立数据包模式）",
         "没有标签= 进游戏后本曲不会被自动驱动。若这是要挂到已有宿主包的 lemon 兼容交付物，"
         "那就正常——但宿主必须每刻自己调用 %s/tick" % full, warn=True)
    if has_tags:
        try:
            vals = json.loads(src.read(tag_dir + "/tick.json")).get("values", [])
        except Exception:
            vals = []
        item("%s/tick" % full in vals, "tick.json 指向 %s/tick" % full,
             "标签里的路径要写成 <命名空间>:<路径>（不带 function/ 目录、不带 .mcfunction）")
    if fdir and src.has("data/%s/%s/%s/init.mcfunction" % (a.namespace, fdir, path)):
        init = src.read("data/%s/%s/%s/init.mcfunction" % (a.namespace, fdir, path))
        item(("#speed nbs_s %d" % a.speed) in init.replace("  ", " "),
             "init.mcfunction 里 #speed nbs_s = %d" % a.speed,
             "#speed 没设 → 每刻 nbs_s 加 0 → 所有音符挤在第 0 刻（听起来是'啪'一声就没了）")
        for obj in ("music_type", "nbs_s", "nbs_t"):
            item(("objectives add %s" % obj) in init, "init 建了记分板目标 %s" % obj,
                 "缺目标的后果是 tick.mcfunction 报错、整曲不发声")
    if fdir and src.has("data/%s/%s/%s/play.mcfunction" % (a.namespace, fdir, path)):
        pl = src.read("data/%s/%s/%s/play.mcfunction" % (a.namespace, fdir, path))
        got = None
        for ln in pl.splitlines():
            if "music_type" in ln and "set" in ln:
                got = ln.split()[-1]
        if a.song_id is not None:
            item(got == str(a.song_id), "play.mcfunction 的 song_id = %s（期望 %s）" % (got, a.song_id),
                 "song_id 对不上 → tick.mcfunction 的 if 守卫永远不成立 → 完全没声音")

    # ---------- 4. 深度检查（交给 validate_pack.py） ----------
    print("\n[4] 深度检查（tree↔notes 一致性 + 树状态机模拟）")
    if src.zip:
        print(" ! zip 输入跳过此项；解压后单独跑：python3 scripts/validate_pack.py --pack <目录> ...")
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
        item(r.returncode == 0, "validate_pack.py 通过",
             "把下面它的输出贴出来看具体哪条不过；最常见的是叶子写成 2 格宽导致相邻 tick 静音")
        for ln in out.splitlines():
            if ln.startswith("FAIL") or ln.strip().startswith("-") or "ALL CHECKS" in ln:
                print("     %s" % ln.strip())

    # ---------- 5. 装进世界了吗 ----------
    if a.world_dir:
        print("\n[5] 是否装进世界")
        base = os.path.basename(os.path.normpath(a.pack))
        cand = os.path.join(a.world_dir, base)
        item(os.path.exists(cand), "存档 datapacks/ 下有 %s" % base,
             "把 zip（或解压出的文件夹）放进 %s 后必须 /reload" % a.world_dir)
        if os.path.isdir(a.world_dir):
            others = [d for d in os.listdir(a.world_dir) if os.path.isdir(os.path.join(a.world_dir, d))]
            print("     datapacks/ 现有: %s" % (", ".join(others) or "(空)"))

    # ---------- 6. 进游戏怎么办 ----------
    print("\n[6] 进游戏后按顺序敲（顺序错了就是没声音）")
    print("     1) /reload                                  （改了任何文件都要重敲）")
    print("     2) /datapack list                            （列表里没有它 = 回到 [2] 看 pack.mcmeta）")
    if a.mc_version and modern is False:
        print("     3) /tick rate 默认 20，本曲按 #speed %d 制作，无需改" % a.speed)
    print("     3) /function %s/play" % full)
    print("     4) 想停: /function %s/stop" % full)
    print("     5) 静音: /tag <玩家> add no_music")
    if a.mc_version and tuple(int(x) for x in a.mc_version.split(".")) >= (1, 20, 3):
        print("     ※ 若用了 --tick-rate 80 制作，必须先 /tick rate 80（退出重进会重置回 20）")

    # ---------- 7. 症状速查 ----------
    print("\n[7] 症状 → 原因速查")
    for sym, cause in [
        ("/datapack list 里根本没有它", "pack.mcmeta 缺失/JSON 不合法/版本写法不对（见 [2]）"),
        ("补全里没有 %s" % full, "目录名 function vs functions 弄反了，或标签没被 /reload 读到"),
        ("play 之后完全没声音", "① tick.json 没指向本曲 ② #speed 没设 ③ song_id 对不上 ④ 玩家有 no_music 标签"),
        ("响一下就没了", "#speed nbs_s 是 0 或缺 → nbs_s 不增长"),
        ("整曲速度不对（快/慢整数倍）", "#speed 与制作时不一致；用 --tick-rate 制作的没敲 /tick rate"),
        ("个别音符不响", "叶子写成 2 格宽（相邻 tick 静音）；或音域超界被夹取；或同 tick 同乐器同音高被去重"),
        ("某个音高听起来不对", "超音域被夹到边界，而不是折八度——用 generate.py 的 WARN 行确认"),
        ("声音糊/爆", "鼓音量太大（踩镲建议 0.25）；同刻 playsound 过多（上限 255）"),
        ("/reload 刷'目标已存在'", "正常：init 每次都 add objective，不影响播放"),
        ("播放中 /reload 后错乱", "状态残留：重新 /function .../play 一次即可"),
    ]:
        print("     %-28s %s" % (sym, cause))

    print("\n" + "=" * 60)
    if problems:
        print("发现 %d 个问题（上面标 ✗ 的项）:" % len(problems))
        for p in problems:
            print("  ✗ %s" % p)
        return 1
    print("全部通过。进游戏按 [6] 的顺序敲命令即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
