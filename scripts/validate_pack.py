#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前自检：tree <-> notes 一致性、乐器白名单/音域、CRLF、标签、song_id，
并用树状态机模拟证明每个音符 tick 在正确的游戏 tick 恰好触发一次。

用法（独立数据包）：
    python3 scripts/validate_pack.py --pack out --namespace minecraft --song lemon \
        --song-id 8 --speed 80 --mc-version 26.2
用法（lemon 兼容模式，交付物只是歌曲文件夹）：
    python3 scripts/validate_pack.py --pack out/music/lemon --song lemon --song-id 8

全部通过退出码 0，否则 1。仅用标准库。
"""
import argparse, collections, json, math, os, re, sys

try:            # Windows 控制台默认 GBK：让非 GBK 字符降级为 ?，而不是直接抛异常
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# 乐器白名单：inst -> (use-count 基准 MIDI, 最低 MC 版本)
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
# sound event 名 -> 乐器
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
    """返回 (歌曲目录, 数据包根目录或 None)。"""
    cand = os.path.join(pack, "data", ns, "function", path)
    if os.path.isdir(os.path.join(cand, "notes")) and os.path.isdir(os.path.join(cand, "tree")):
        return cand, pack
    if os.path.isdir(os.path.join(pack, "notes")) and os.path.isdir(os.path.join(pack, "tree")):
        return pack, None                       # lemon 兼容模式：交付物就是歌曲文件夹
    for dp, dns, _ in os.walk(pack):
        if os.path.basename(dp) == song and "notes" in dns and "tree" in dns:
            return dp, None                      # 只在目录树里找到歌曲文件夹，不当作数据包根
    return None, None


def main():
    ap = argparse.ArgumentParser(description="红石音乐数据包交付前自检")
    ap.add_argument("--pack", required=True, help="数据包根目录，或 lemon 兼容模式下的歌曲文件夹")
    ap.add_argument("--namespace", default="minecraft")
    ap.add_argument("--path", default=None, help="函数路径，默认 music/<song>")
    ap.add_argument("--song", default=None, help="歌名（用于默认路径与提示）")
    ap.add_argument("--song-id", type=int, default=None, help="play/tick 里应出现的 music_type 值")
    ap.add_argument("--speed", type=int, default=80, help="#speed nbs_s 的值，默认 80")
    ap.add_argument("--mc-version", default=None, help="目标 MC 版本，用于校验乐器与 pack.mcmeta 写法")
    ap.add_argument("--no-simulate", action="store_true", help="跳过树状态机模拟")
    a = ap.parse_args()
    if not a.song:
        a.song = os.path.basename(os.path.normpath(a.pack))
    path = a.path or ("music/" + a.song)
    full = "%s:%s" % (a.namespace, path)

    fail, warn = [], []
    song_dir, pack_root = locate(a.pack, a.namespace, path, a.song)
    if not song_dir:
        print("FAIL: 在 %s 里找不到含 notes/ 与 tree/ 的歌曲目录（可用 --path 指定）" % a.pack)
        return 1
    print("歌曲目录: %s" % song_dir)

    notes_dir = os.path.join(song_dir, "notes")
    tree_dir = os.path.join(song_dir, "tree")
    notes = sorted(int(f[:-11]) for f in os.listdir(notes_dir) if f.endswith(".mcfunction"))
    trees = sorted(f[:-11] for f in os.listdir(tree_dir) if f.endswith(".mcfunction"))
    if not notes:
        print("FAIL: notes/ 为空")
        return 1

    # ---- 1. CRLF
    for dp, _, fs in os.walk(os.path.dirname(song_dir) if pack_root else song_dir):
        if pack_root and not dp.startswith(pack_root):
            continue
        for fn in fs:
            if not fn.endswith(".mcfunction"):
                continue
            p = os.path.join(dp, fn)
            b = open(p, "rb").read()
            if b"\n" in b and b"\r\n" not in b:
                fail.append("LF 行尾（应为 CRLF）: %s" % p)

    # ---- 2. tree 引用 notes 恰好一次（叶子必须 1 格宽，否则相邻对 (2k,2k+1) 的第二个 tick 静音）
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
            fail.append("tree/%s 里有无法解析的行: %s" % (name, ln))
    bad_ref = [t for t in notes if ref[t] != 1]
    if bad_ref:
        fail.append("被 tree 引用次数 != 1 的 notes: %d 个（前 10: %s）—— 0 次即永久静音，"
                    "最常见原因是叶子写成了 2 格宽（见 references/format_spec.md §A）"
                    % (len(bad_ref), bad_ref[:10]))
    ghost = [t for t in ref if t not in notes]
    if ghost:
        fail.append("tree 引用了不存在的 notes: %s" % ghost[:10])

    # ---- 3. 树根可达性 + 悬空子节点
    tick_path = os.path.join(song_dir, "tick.mcfunction")
    root = None
    if os.path.isfile(tick_path):
        for m in re.finditer(r"function %s/tree/(\d+_\d+)" % re.escape(full),
                             read_text(tick_path)):
            root = m.group(1)
    if root is None:
        warn.append("没能在 %s/tick.mcfunction 里找到树根调用（lemon 兼容模式可能由宿主调用）" % path)
    for name, items in nodes.items():
        for it in items:
            if it[0] == "node" and it[3] not in nodes:
                fail.append("tree/%s 指向不存在的子节点 %s" % (name, it[3]))
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
            fail.append("从根 %s 不可达的 tree 节点: %d 个（前 10: %s）" % (root, len(un), un[:10]))
    elif root:
        fail.append("树根 %s 不存在" % root)

    # ---- 4. playsound 行：白名单、音域、音量
    vols = collections.defaultdict(set)
    spans = collections.defaultdict(lambda: [99, -1])
    nlines = 0
    for t in notes:
        for ln in read_text(os.path.join(notes_dir, "%d.mcfunction" % t)).split("\r\n"):
            if not ln.strip() or ln.startswith("scoreboard") or ln.startswith("function"):
                continue
            m = PS_RE.match(ln)
            if not m:
                fail.append("notes/%d 有异常行: %s" % (t, ln))
                continue
            nlines += 1
            ev, vol, pitch = m.group(2), float(m.group(3)), float(m.group(4))
            inst = SOUND2INST.get(ev)
            if inst is None:
                fail.append("notes/%d 用了白名单外的音效 %s" % (t, ev))
                continue
            if a.mc_version and vtuple(a.mc_version) < vtuple(INSTRUMENTS[inst][1]):
                fail.append("notes/%d 的 %s 需要 MC %s+（目标 %s）" % (t, inst, INSTRUMENTS[inst][1], a.mc_version))
            if not 0.5 <= pitch <= 2.0:
                fail.append("notes/%d 的 pitch=%s 超出 [0.5,2.0]" % (t, pitch))
                continue
            uc = int(round(12 + 12 * math.log(pitch, 2)))
            if not 0 <= uc <= 24:
                fail.append("notes/%d 的 %s use-count=%d 超出 [0,24]（未做八度折叠？）" % (t, inst, uc))
            if inst in HEADS:
                warn.append("notes/%d 用了头颅乐器 %s（无视 pitch）" % (t, inst))
            vols[inst].add(vol)
            spans[inst][0] = min(spans[inst][0], uc)
            spans[inst][1] = max(spans[inst][1], uc)

    # ---- 5. play/stop/tick 的 song_id 与末 tick auto_stop
    play_p, stop_p, tick_p = (os.path.join(song_dir, x) for x in
                              ("play.mcfunction", "stop.mcfunction", "tick.mcfunction"))
    sid = None
    if os.path.isfile(play_p):
        m = re.search(r"scoreboard players set music_progress music_type (-?\d+)", read_text(play_p))
        sid = int(m.group(1)) if m else None
    if a.song_id is not None:
        if sid != a.song_id:
            fail.append("play.mcfunction 的 song_id=%s 与期望 %d 不符" % (sid, a.song_id))
        if os.path.isfile(tick_p) and ("matches %d run" % a.song_id) not in read_text(tick_p):
            fail.append("tick.mcfunction 没有 if music_type matches %d 守卫" % a.song_id)
        if os.path.isfile(stop_p) and ("matches %d run" % a.song_id) in read_text(stop_p):
            warn.append("stop.mcfunction 也带 song_id 守卫（上游约定 stop 不守卫）")
    last = [l for l in read_text(os.path.join(notes_dir, "%d.mcfunction" % notes[-1])).split("\r\n") if l.strip()]
    if last and not STOP_RE.match(last[-1]):
        fail.append("末 tick notes/%d 最后一行不是 function .../stop" % notes[-1])

    # ---- 6. pack.mcmeta 与标签（可选：lemon 兼容交付物本来就没有）
    if pack_root:
        mc = os.path.join(pack_root, "pack.mcmeta")
        if not os.path.isfile(mc):
            fail.append("缺少 pack.mcmeta")
        else:
            try:
                p = json.loads(read_text(mc))["pack"]
            except Exception as e:
                p = None
                fail.append("pack.mcmeta 不是合法 JSON: %s" % e)
            if p is not None:
                modern = bool(a.mc_version and vtuple(a.mc_version) >= (1, 21, 9))
                if modern or ("min_format" in p or "max_format" in p):
                    if "min_format" not in p or "max_format" not in p:
                        fail.append("≥1.21.9 必须写 min_format 与 max_format（数组 [主,次]）")
                    else:
                        for k in ("min_format", "max_format"):
                            if not (isinstance(p[k], list) and len(p[k]) == 2 and all(isinstance(x, int) for x in p[k])):
                                fail.append("%s 必须是 [主,次] 两个整数（不能写小数 107.1）: %r" % (k, p[k]))
                        if p["min_format"] != p["max_format"]:
                            warn.append("min_format %s != max_format %s（只在确实跨版本时才该如此）" % (p["min_format"], p["max_format"]))
                    for k in ("pack_format", "supported_formats"):
                        if k in p:
                            fail.append("≥1.21.9 的现代写法不应再出现 %s" % k)
                else:
                    if "pack_format" not in p:
                        fail.append("≤1.21.8 需要 pack_format")
                    for k in ("min_format", "max_format"):
                        if k in p:
                            fail.append("≤1.21.8 不应出现 %s" % k)
        for tag, target in (("load", "%s/init" % full), ("tick", "%s/tick" % full)):
            tf = os.path.join(pack_root, "data", a.namespace, "tags", "function", tag + ".json")
            if not os.path.isfile(tf):
                warn.append("没有 data/%s/tags/function/%s.json（lemon 兼容模式可忽略）" % (a.namespace, tag))
                continue
            try:
                vals = json.loads(read_text(tf)).get("values", [])
            except Exception as e:
                fail.append("%s 不是合法 JSON: %s" % (tf, e))
                continue
            for v in vals:
                ns, _, pth = str(v).partition(":")
                if not os.path.isfile(os.path.join(pack_root, "data", ns, "function", pth + ".mcfunction")):
                    fail.append("tags/function/%s.json 指向不存在的函数 %s" % (tag, v))
            if target not in vals:
                warn.append("tags/function/%s.json 未包含 %s" % (tag, target))

    # ---- 7. 树状态机模拟：每个 tick 是否在正确的游戏 tick 恰好触发一次
    fired = collections.defaultdict(list)
    sim_note = "-"
    if not a.no_simulate and root and root in nodes:
        by_name = nodes
        maxt = notes[-1]
        # 模拟"刚执行过 play.mcfunction"的状态：nbs_s=0、nbs_t=-1（None 表示 reset 后未赋值 = 不匹配任何区间）
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

        for T in range(1, maxt + 4):          # 多跑几刻，确认不会重复触发
            state["nbs_s"] += a.speed
            call_tree(root)
        once = [t for t in notes if len(fired[t]) != 1]
        if once:
            fail.append("模拟结果：%d 个 notes 触发次数 != 1（前 10: %s）—— 0 次=静音，>1 次=重复播放"
                        % (len(once), [(t, len(fired[t])) for t in once[:10]]))
        wrong = []
        for t in notes:
            if len(fired[t]) == 1:
                # tick.mcfunction 先 nbs_s += #speed 再调树；叶子窗口 80t..80t+160
                # → 首次匹配 T = ceil(80t/speed)，且 T 至少为 1（t=0 的音符也在第一刻才发）
                exp = max(1, (80 * t + a.speed - 1) // a.speed)
                if fired[t][0] != exp:
                    wrong.append((t, fired[t][0], exp))
        if wrong:
            warn.append("%d 个 notes 的触发时刻与期望差 >0 tick（前 5: %s）"
                        % (len(wrong), wrong[:5]))
        sim_note = "每个 tick 恰好触发一次" if not once else "有异常"

    # ---- 报告
    print("notes: %d   tree 节点: %d   可达: %d   playsound 行: %d"
          % (len(notes), len(trees), len(reachable), nlines))
    print("tick 范围: %d..%d  时长 %.1fs   #speed=%d" % (notes[0], notes[-1], notes[-1] / 20.0, a.speed))
    print("每个乐器的音量: %s" % {k: sorted(v) for k, v in sorted(vols.items())})
    print("每个乐器的 use-count 区间: %s"
          % {k: tuple(v) for k, v in sorted(spans.items()) if v[1] >= 0})
    if not a.no_simulate:
        print("树状态机模拟: %s" % sim_note)
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
