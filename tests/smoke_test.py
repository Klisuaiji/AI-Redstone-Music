#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端冒烟测试（纯标准库，可直接当 CI 用）：

    python3 tests/smoke_test.py

覆盖：
  1. song.json → generate.py → validate_pack.py 全绿，且每个 notes 文件都被 tree 引用恰好一次
  2. **回归测试**：把 tree 改回上游那种 2 格宽叶子 → validate_pack.py 必须报错
     （这是历史上"相邻 tick 的第二个音符永久静音"的 bug，必须一直有人看着它）
  3. make_datapack.py：26.2 出 min_format/max_format，1.20.4 出 pack_format + functions/ 目录
  4. pack.mcmeta 写法写错时 validate_pack.py 必须报错（26.2 只写 pack_format 是错的）
"""
import json, os, re, shutil, subprocess, sys, uuid, zipfile

try:            # 控制台是 GBK 时，非 GBK 字符降级为 ?，不要让测试自己崩在 print 上
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
S = os.path.join(ROOT, "scripts")
PY = sys.executable

results = []


def run(cmd):
    # 子进程一律用 UTF-8 输出（否则 Windows 下按 GBK 写管道，回读会变成乱码），
    # 这样断言里可以直接写中文。
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail and not ok else ""))


def make_song(path, name="demo", song_id=7):
    """刻意让 0/1/2 三个 tick 都相邻 —— 上游 2 格宽叶子会在这里吃掉一个音符。"""
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
    """tree 里每个 notes/<t> 被引用了多少次。"""
    ref = {}
    tdir = os.path.join(song_dir, "tree")
    for fn in os.listdir(tdir):
        txt = open(os.path.join(tdir, fn), encoding="utf-8").read()
        for m in re.finditer(r"/notes/(\d+)", txt):
            t = int(m.group(1))
            ref[t] = ref.get(t, 0) + 1
    return ref


def main():
    # 默认在仓库目录下开临时工作区（有些沙箱环境不允许写系统 temp），跑完自动删除。
    # 不用 tempfile.mkdtemp：它以 0700 建目录，在某些 Windows 沙箱里 ACL 会拦住后续写入。
    base = os.environ.get("RSM_SMOKE_DIR") or ROOT
    tmp = os.path.join(base, ".rsm-smoke-" + uuid.uuid4().hex[:8])
    os.makedirs(tmp)
    print("工作目录: %s\n" % tmp)
    try:
        songp = os.path.join(tmp, "demo.song.json")
        make_song(songp)
        out = os.path.join(tmp, "out")

        # ---------- 1. 生成 + 自检 ----------
        print("[1] generate.py → validate_pack.py")
        code, log = run([PY, os.path.join(S, "generate.py"), songp, "-o", os.path.join(out, "music", "demo")])
        check("generate.py 退出码 0", code == 0, log.strip()[-200:])
        song_dir = os.path.join(out, "music", "demo")
        check("notes/ 与 tree/ 都生成了",
              os.path.isdir(os.path.join(song_dir, "notes")) and os.path.isdir(os.path.join(song_dir, "tree")))

        notes = sorted(int(f[:-11]) for f in os.listdir(os.path.join(song_dir, "notes")))
        ref = tree_refs(song_dir)
        bad = [t for t in notes if ref.get(t, 0) != 1]
        check("每个 notes 文件都被 tree 恰好引用 1 次（含相邻 tick 0/1/2）", not bad, "异常: %s" % bad)

        code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", out,
                         "--namespace", "minecraft", "--song", "demo", "--song-id", "7", "--speed", "80",
                         "--mc-version", "26.2"])
        check("validate_pack.py 全绿", code == 0, log.strip()[-300:])
        check("自检里跑到了树状态机模拟", "树状态机模拟" in log or "ALL CHECKS PASSED" in log)

        # ---------- 2. 回归：2 格宽叶子必须被抓出来 ----------
        print("\n[2] 回归测试：把 tree 改回 2 格宽叶子（历史上的静音 bug）")
        bug = os.path.join(tmp, "buggy")
        shutil.copytree(out, bug)
        bdir = os.path.join(bug, "music", "demo", "tree")
        for f in os.listdir(bdir):
            os.remove(os.path.join(bdir, f))
        # 复刻上游算法：区间宽 2 且只发 rng[0]
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
        check("2 格宽叶子被判定为 FAIL", code != 0)
        check("报错点明了 notes/1 静音", "notes/1" in log or "静音" in log, log.strip()[-300:])

        # ---------- 3. make_datapack：两代 pack.mcmeta ----------
        print("\n[3] make_datapack.py")
        p26 = os.path.join(tmp, "pack26")
        code, log = run([PY, os.path.join(S, "make_datapack.py"), songp, "-o", p26, "--mc-version", "26.2"])
        check("make_datapack.py(26.2) 退出码 0", code == 0, log.strip()[-300:])
        mc = json.load(open(os.path.join(p26, "pack.mcmeta"), encoding="utf-8"))["pack"]
        check("26.2 用 min_format/max_format = [107,1]",
              mc.get("min_format") == [107, 1] and mc.get("max_format") == [107, 1], str(mc))
        check("26.2 不出现 pack_format/supported_formats",
              "pack_format" not in mc and "supported_formats" not in mc)
        check("26.2 目录用 function/ 与 tags/function/",
              os.path.isdir(os.path.join(p26, "data", "minecraft", "function", "music", "demo")) and
              os.path.isfile(os.path.join(p26, "data", "minecraft", "tags", "function", "tick.json")))
        z = os.path.join(tmp, "pack26.zip")
        check("生成了 zip 且 pack.mcmeta 在 zip 根目录",
              os.path.isfile(z) and "pack.mcmeta" in zipfile.ZipFile(z).namelist())
        code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", p26, "--namespace", "minecraft",
                         "--song", "demo", "--song-id", "7", "--speed", "80", "--mc-version", "26.2"])
        check("打出来的 26.2 数据包自检全绿", code == 0, log.strip()[-300:])

        p120 = os.path.join(tmp, "pack1204")
        code, log = run([PY, os.path.join(S, "make_datapack.py"), songp, "-o", p120,
                         "--mc-version", "1.20.4", "--no-zip"])
        mc = json.load(open(os.path.join(p120, "pack.mcmeta"), encoding="utf-8"))["pack"]
        check("1.20.4 用 pack_format = 26", mc.get("pack_format") == 26, str(mc))
        check("1.20.4 目录用 functions/ 与 tags/functions/",
              os.path.isdir(os.path.join(p120, "data", "minecraft", "functions", "music", "demo")) and
              os.path.isfile(os.path.join(p120, "data", "minecraft", "tags", "functions", "tick.json")))

        # ---------- 4. pack.mcmeta 写法写错必须报错 ----------
        print("\n[4] pack.mcmeta 写法校验")
        bad = os.path.join(tmp, "badmeta")
        shutil.copytree(p26, bad)
        with open(os.path.join(bad, "pack.mcmeta"), "w", encoding="utf-8") as f:
            json.dump({"pack": {"pack_format": 107, "description": "wrong"}}, f)
        code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", bad, "--namespace", "minecraft",
                         "--song", "demo", "--song-id", "7", "--speed", "80", "--mc-version", "26.2"])
        check("26.2 只写 pack_format 被判 FAIL", code != 0, log.strip()[-200:])

        # ---------- 5. 真实 MIDI 走一遍（examples/demo.mid） ----------
        print("\n[5] 示例 MIDI 端到端（scan → midi_to_song → make_datapack → validate）")
        mid = os.path.join(ROOT, "examples", "demo.mid")
        if not os.path.isfile(mid):
            check("examples/demo.mid 存在", False, "先跑 python3 tests/gen_demo_midi.py examples/demo.mid")
        else:
            code, log = run([PY, os.path.join(S, "scan_midi.py"), mid])
            check("scan_midi.py 跑通并给出判定", code == 0 and "判定" in log, log.strip()[-200:])
            song2p = os.path.join(tmp, "demo2.song.json")
            code, log = run([PY, os.path.join(S, "midi_to_song.py"), mid, "-o", song2p,
                             "--name", "demo", "--song-id", "8", "--mc-version", "26.2"])
            check("midi_to_song.py 跑通", code == 0, log.strip()[-200:])
            song2 = json.load(open(song2p, encoding="utf-8"))
            n2 = sum(len(t["notes"]) for t in song2["tracks"])
            check("产出的 song.json 有音符（%d 个）" % n2, n2 > 100)
            ticks2 = sorted({n["t"] for t in song2["tracks"] for n in t["notes"]})
            adj2 = [b for a, b in zip(ticks2, ticks2[1:]) if b - a == 1]
            check("示例 MIDI 产生了相邻音符 tick（%d 对，正好踩中静音 bug 场景）" % len(adj2), len(adj2) > 0)
            p2 = os.path.join(tmp, "demo-pack")
            code, log = run([PY, os.path.join(S, "make_datapack.py"), song2p, "-o", p2,
                             "--mc-version", "26.2", "--no-zip"])
            check("make_datapack.py 处理真实 MIDI 产物", code == 0, log.strip()[-200:])
            code, log = run([PY, os.path.join(S, "validate_pack.py"), "--pack", p2, "--namespace", "minecraft",
                             "--song", "demo", "--song-id", "8", "--speed", "80", "--mc-version", "26.2"])
            check("该数据包自检全绿", code == 0, log.strip()[-300:])
            code, log = run([PY, os.path.join(S, "doctor.py"), "--pack", p2, "--mc-version", "26.2",
                             "--song", "demo", "--song-id", "8", "--speed", "80"])
            check("doctor.py 全 [OK]", code == 0 and "[X]" not in log, log.strip()[-200:])
            code, log = run([PY, os.path.join(S, "midi_to_song.py"), mid, "-o", os.path.join(tmp, "tr80.json"),
                             "--name", "demo", "--song-id", "8", "--tick-rate", "80"])
            check("--tick-rate 80 可用（网格 12.5ms）", code == 0 and "12.50 ms" in log, log.strip()[-200:])

        # ---------- 6. 红石音乐盒：注册歌曲 → 静态检查 ----------
        print("\n[6] 红石音乐盒（通用框架 + 注册歌曲）")
        box_src = os.path.join(ROOT, "examples", "musicbox", "datapack")
        if not os.path.isdir(box_src):
            check("examples/musicbox/datapack 存在", False, "缺少音乐盒框架")
        else:
            code, log = run([PY, os.path.join(S, "check_refs.py"), box_src])
            check("空盒子的函数引用全部可解析", code == 0, log.strip()[-200:])
            box = os.path.join(tmp, "box")
            shutil.copytree(box_src, box)
            lrc = os.path.join(tmp, "t.lrc")
            with open(lrc, "w", encoding="utf-8") as f:
                f.write("[00:00.00]第一句\n[00:02.50]第二句\n")
            code, log = run([PY, os.path.join(S, "add_to_musicbox.py"), "--box", box,
                             "--song", mid, "--name", "Smoke Test Song", "--lrc", lrc])
            check("add_to_musicbox.py 注册 MIDI + 歌词", code == 0, log.strip()[-200:])
            code, log = run([PY, os.path.join(S, "check_refs.py"), box])
            check("注册后引用仍全部可解析", code == 0, log.strip()[-200:])
            mx = open(os.path.join(box, "data/rmb/function/song/max.mcfunction"), encoding="utf-8").read()
            check("#max 被写成 1", "#max mb_cfg 1" in mx, mx.strip()[-120:])
            songdir = os.path.join(box, "data/rmb/function/song/1")
            check("歌曲四件套齐全（play/tick/stop/lrc）",
                  all(os.path.isfile(os.path.join(songdir, f)) for f in
                      ("play.mcfunction", "tick.mcfunction", "stop.mcfunction", "lrc.mcfunction")))
            lrcf = open(os.path.join(songdir, "lrc.mcfunction"), encoding="utf-8").read()
            check("歌词按 nbs_s 排好（2.5s → 50 tick → 4000）", "4000.." in lrcf, lrcf.strip()[-160:])
            menu = open(os.path.join(box, "data/rmb/function/box/menu_list.mcfunction"), encoding="utf-8").read()
            check("菜单里出现可点击的歌名", "/trigger play set 1" in menu and "Smoke Test Song" in menu)
            code, log = run([PY, os.path.join(S, "add_to_musicbox.py"), "--box", box,
                             "--song", mid, "--name", "Second"])
            check("自动分配第二个编号", code == 0 and "[2]" in log, log.strip()[-160:])
            code, log = run([PY, os.path.join(S, "add_to_musicbox.py"), "--box", box, "--remove", "1"])
            check("可以移除曲目", code == 0, log.strip()[-160:])
            code, log = run([PY, os.path.join(S, "check_refs.py"), box])
            check("移除后引用仍全部可解析", code == 0, log.strip()[-200:])
            code, log = run([PY, os.path.join(S, "add_to_musicbox.py"), "--box", box,
                             "--song", mid, "--name", "dup", "--id", "2"])
            check("编号冲突会被拒绝", code != 0)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    nfail = sum(1 for _, ok, _ in results if not ok)
    print("\n%d 项检查，%d 项失败" % (len(results), nfail))
    if nfail:
        for name, _, detail in results:
            if not _:
                print("  FAIL: %s\n        %s" % (name, detail))
        return 1
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
