#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MIDI 体检报告：编曲前先看一眼这份输出，能把"该保留哪些轨、映射成什么乐器、音域会不会溢出、
量化误差有多大"全部定下来（对应 SKILL.md 第二步）。

用法：
    python3 scripts/scan_midi.py 歌曲.mid
    python3 scripts/scan_midi.py 歌曲.mid --json report.json

输出内容：文件头 / tempo / 时长 / 逐轨清单（名称·声道·音色号·音符数·音高范围·八度分布）/
鼓组 GM 直方图 / 节奏网格与量化误差 / 声部映射建议。
仅用标准库。
"""
import argparse, collections, json, math, os, sys

try:            # Windows 控制台默认 GBK：让非 GBK 字符（⚠ 等）降级为 ?，而不是直接抛异常
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from midilib import read_midi, gm_drum_name

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# 音符盒音域上下限（F#1 – F#7），见 references/instruments.md
NB_LO, NB_HI = 30, 102
# 各乐器基准（use-count 0 的音高）与可及音域 = base..base+24
BASE = {"harp": 54, "bass": 30, "basedrum": 54, "snare": 54, "hat": 54, "bell": 78,
        "chime": 78, "flute": 66, "guitar": 42, "xylophone": 78, "iron_xylophone": 54,
        "cow_bell": 54, "didgeridoo": 30, "bit": 54, "banjo": 54, "pling": 54}


def nn(p):
    return "%s%d" % (NAMES[p % 12], p // 12 - 1)


def gcd_all(xs):
    g = 0
    for x in xs:
        g = math.gcd(g, int(abs(x)))
    return g


# 常见细分（每四分音符 N 等分）→ 中文名
SUBDIV = {1: "四分", 2: "八分", 3: "八分三连", 4: "十六分", 6: "十六分三连", 8: "三十二分",
          12: "三十二分三连", 16: "六十四分", 24: "六十四分三连", 32: "128 分",
          48: "128 分三连", 64: "256 分", 96: "256 分三连", 100: "1/100 四分", 128: "512 分",
          192: "512 分三连", 200: "1/200 四分"}


def fit_grid(rel, division):
    """所有 onset 相对首个 onset 的偏移，能否被某个音乐细分网格解释？

    返回 (每四分音符等分数 N, 网格 tick 数, 覆盖率)，N 取"最粗且覆盖率 ≥98%"的那个。
    直接算 gcd 会被"网格本来是非整数、导出时四舍五入成整数"毁掉（差值在 4/5 tick 之间跳，
    gcd 退化成 1），所以这里枚举音乐上合理的细分并允许 ±1 tick 的取整残差。
    """
    best = None
    for N in sorted(SUBDIV):        # N 升序 = 网格由粗到细，取第一个满足的就是最粗的
        g = division / float(N)
        tol = max(1.0, g * 0.02)
        hit = 0
        for r in rel:
            k = round(r / g)
            if abs(r - k * g) <= tol:
                hit += 1
        cov = hit / float(len(rel))
        if cov >= 0.98:
            best = (N, g, cov)
            break
    return best


def main():
    ap = argparse.ArgumentParser(description="MIDI 体检报告（编曲前看一眼）")
    ap.add_argument("midi")
    ap.add_argument("--json", default=None, help="把结构化结果写到该 JSON 文件")
    ap.add_argument("--speed", type=int, default=80, help="时轴换算用的 #speed（默认 80）")
    a = ap.parse_args()

    m = read_midi(a.midi)
    rep = {}
    print("=== %s ===" % a.midi)
    print("header: format=%d  MTrk 数=%d（声明 %d）  division=%d ticks/四分音符"
          % (m.fmt, len(m.tracks), m.declared_ntrks, m.division))
    print("tempo: %s" % " | ".join("%.3f BPM @tick %d" % (60e6 / u, t) for t, u in m.tempos))
    last = m.last_note_tick()
    print("时长: %.2f s（最后一个 note-on）  音符总数: %d（只统计 note-on）"
          % (m.sec_at(last), m.note_count))
    rep["file"] = a.midi
    rep["division"] = m.division
    rep["tempos"] = [{"tick": t, "bpm": 60e6 / u} for t, u in m.tempos]
    rep["duration_s"] = m.sec_at(last)
    rep["note_count"] = m.note_count

    # ---------- 轨道清单 ----------
    print("\n--- 轨道清单 ---")
    print(" %-3s %-30s %-6s %-8s %-6s %-18s %-24s %s"
          % ("#", "名称", "声道", "音色号", "音符", "音高范围", "八度分布(八度:个数)", "起→止"))
    tracks_rep = []
    for t in m.tracks:
        if not t.notes:
            print(" %-3d %-30s %-6s %-8s %-6d %-18s %-24s %s"
                  % (t.index, t.name[:30], "-", "-", 0, "-", "-", "（空轨：tempo/标记）"))
            continue
        ps = t.pitches()
        octs = collections.Counter(n.pitch // 12 - 1 for n in t.notes)
        chans = ",".join(str(c) for c in sorted(t.channels))
        progs = ",".join(str(p) for _, p in t.programs) or "-"
        first, lastt = t.notes[0].tick, max(n.tick for n in t.notes)
        print(" %-3d %-30s %-6s %-8s %-6d %-18s %-24s %.2fs → %.2fs"
              % (t.index, t.name[:30], chans, progs, len(t.notes),
                 "%d..%d (%s..%s)" % (ps[0], ps[-1], nn(ps[0]), nn(ps[-1])),
                 " ".join("%d:%d" % (k, v) for k, v in sorted(octs.items())),
                 m.sec_at(first), m.sec_at(lastt)))
        tracks_rep.append({"index": t.index, "name": t.name, "notes": len(t.notes),
                           "channels": sorted(t.channels),
                           "programs": [p for _, p in t.programs],
                           "pitch_min": ps[0], "pitch_max": ps[-1],
                           "octaves": {str(k): v for k, v in sorted(octs.items())},
                           "is_drum": t.is_drum})
    rep["tracks"] = tracks_rep

    # ---------- 鼓组 ----------
    drum = collections.Counter()
    for t in m.tracks:
        for n in t.notes:
            if n.chan == 9:
                drum[n.pitch] += 1
    if drum:
        print("\n--- 打击乐（GM 音高）---")
        line = []
        for p, c in sorted(drum.items()):
            line.append("%d %s ×%d" % (p, gm_drum_name(p), c))
        print(" " + " | ".join(line))
        print(" 映射建议: 36→basedrum 0.6 | 38/40→snare 0.5 | 其余→hat 0.25（鼓宁小勿大）")
        rep["drums"] = {str(k): v for k, v in sorted(drum.items())}

    # ---------- 节奏网格 ----------
    onsets = sorted(set(n.tick for t in m.tracks for n in t.notes))
    if len(onsets) > 1:
        tps = m.ticks_per_second(0)
        bpm = m.bpm_at(0)
        rel = [o - onsets[0] for o in onsets]
        g_rel = gcd_all(rel)
        fit = fit_grid(rel, m.division)
        sixteenth = m.division / 4.0
        on16 = sum(1 for o in onsets if abs(o / sixteenth - round(o / sixteenth)) < 1e-6)
        per_game_tick = tps / 20.0
        print("\n--- 节奏网格 ---")
        print(" onset 数（去重）: %d" % len(onsets))
        if fit:
            N, g, cov = fit
            name = SUBDIV.get(N, "%d 分" % N)
            std = N in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 192)
            print(" 最贴合的网格: 1/%d 四分音符（%s）= %.3f MIDI tick = %.2f ms，覆盖 %.1f%% 的 onset%s"
                  % (N, name, g, g / tps * 1000.0, cov * 100.0,
                     "" if std else " ← 非标准细分，多半是转谱工具的人性化/量化输出"))
        else:
            print(" 没有找到覆盖率 ≥98% 的规整网格（gcd(onset 差值)=%d tick，说明演奏相当自由）" % g_rel)
        print(" 16 分音符网格: %.0f tick，恰好落在其上的 onset 占 %.0f%%"
              % (sixteenth, 100.0 * on16 / len(onsets)))
        print(" 时轴: 1 游戏 tick = %.1f MIDI tick；%.3f BPM 下 1 个 16 分 = %.3f 游戏 tick"
              % (per_game_tick, bpm, sixteenth / per_game_tick))
        err = per_game_tick / 2.0 / tps * 1000.0
        print(" 量化到 20 tps 的最大误差: %.1f ms（半个游戏 tick，物理下限，无法再优化）" % err)
        print(" 推荐写法: time_unit=nbs_s_units + speed=%d（t 即游戏 tick），"
              "t = round(秒 × 20) = round(MIDI tick × 20 / %.1f)" % (a.speed, tps))
        rep["grid"] = {"onsets": len(onsets), "gcd_delta": g_rel,
                       "best_grid": None if not fit else {"subdiv": fit[0], "ticks": fit[1], "coverage": fit[2]},
                       "on_16th_ratio": on16 / len(onsets),
                       "midi_ticks_per_game_tick": per_game_tick,
                       "max_quantize_error_ms": err}

    # ---------- 声部建议 ----------
    print("\n--- 声部映射建议（细节用 midi_to_song.py 生成）---")
    for t in m.tracks:
        if not t.notes:
            continue
        ps = [n.pitch for n in t.notes]
        low = t.name.lower()
        if t.is_drum:
            print(" %d %-28s → 鼓组（basedrum/snare/hat）" % (t.index, t.name[:28]))
            continue
        if "bass" in low or "贝" in low:
            under = sum(1 for p in ps if p < NB_LO)
            extra = "；%d 个音低于 F#1(MIDI 30)，必须升八度" % under if under else ""
            print(" %d %-28s → bass（vol 1.0）%s" % (t.index, t.name[:28], extra))
            continue
        hi = [p for p in ps if p >= 72]
        lo = [p for p in ps if p < 72]
        cand = [i for i, b in BASE.items() if b <= min(ps) and max(ps) <= b + 24 and i in
                ("flute", "pling", "bit", "harp", "bell", "chime")]
        print(" %d %-28s → 拆主旋律/和弦：>=72 的 %d 个音、<72 的 %d 个音"
              % (t.index, t.name[:28], len(hi), len(lo)))
        if cand:
            print("    音域 %d..%d 能被单一乐器覆盖: %s" % (min(ps), max(ps), ", ".join(cand)))
        else:
            print("    音域 %d..%d 单个乐器盖不住（每个乐器只有 25 个半音），"
                  "建议按音区拆分或折八度" % (min(ps), max(ps)))

    # ---------- 判定（一句话结论 + 下一步命令）----------
    print("\n--- 判定 ---")
    melodic = [t for t in m.tracks if t.notes and not t.is_drum and "bass" not in t.name.lower()
               and "贝" not in t.name.lower()]
    has_bass = any(t.notes and ("bass" in t.name.lower() or "贝" in t.name.lower()) for t in m.tracks)
    has_drum = any(t.notes and t.is_drum for t in m.tracks)
    voices = []
    if melodic:
        voices.append("旋律 %d" % len(melodic))
    if has_bass:
        voices.append("贝斯 1")
    if has_drum:
        voices.append("鼓 1")
    # 量化后的真实音符 tick 数（t = round(秒 × 20)）
    ticks = set()
    for t in m.tracks:
        for n in t.notes:
            ticks.add(int(round(m.sec_at(n.tick) * 20.0)))
    print(" 声部: %s（%d 个非空轨）→ 量化到 20 tps 后 %d 个音符 tick"
          % ("、".join(voices) or "无", sum(1 for t in m.tracks if t.notes), len(ticks)))
    if melodic:
        ps = [n.pitch for t in melodic for n in t.notes]
        mel_cands = ("flute", "pling", "bit", "harp", "bell", "chime")

        def best(v, cands):
            """挑一个需要折八度的音最少的乐器，返回 (乐器, 需折八度的音数)。"""
            if not v:
                return None, 0
            bi, bn = None, None
            for i in cands:
                lo, hi = BASE[i], BASE[i] + 24
                n = sum(1 for p in v if not (lo <= p <= hi))
                if bn is None or n < bn:
                    bi, bn = i, n
            return bi, bn

        i_all, n_all = best(ps, mel_cands)
        if max(ps) - min(ps) <= 24 and n_all == 0:
            print(" 主旋律音域 %d..%d（%d 个半音）单乐器可覆盖: %s" % (min(ps), max(ps), max(ps) - min(ps), i_all))
        else:
            hi = [p for p in ps if p >= 72]
            lo = [p for p in ps if p < 72]
            ih, nh = best(hi, mel_cands)
            il, nl = best(lo, ("guitar", "harp", "banjo", "pling", "flute"))
            print(" 主旋律音域 %d..%d 跨 %d 个半音，单个乐器（都只有 25 个半音）盖不住" % (min(ps), max(ps), max(ps) - min(ps)))
            print("   最好单乐器覆盖: %s（%d/%d 个音超出，需折八度）" % (i_all, n_all, len(ps)))
            print("   按 72 拆开更好: >=72 用 %s（%d/%d 超）、<72 用 %s（%d/%d 超）"
                  % (ih, nh, len(hi), il, nl, len(lo)))
    low = [(t.name, n.pitch) for t in m.tracks for n in t.notes if n.pitch < NB_LO]
    if low:
        print(" ⚠ %d 个音低于音符盒音域下限 F#1(MIDI 30)，必须升八度（改名后的音高关系不变）" % len(low))
    if onsets and len(ticks) < len(onsets):
        print(" ⚠ 量化后 tick 数(%d) < onset 数(%d)：有音符被压到同一 tick（20 tps 网格太粗，"
              "可考虑 /tick rate 40/80 细化网格）" % (len(ticks), len(onsets)))
    print(" 下一步: python3 scripts/midi_to_song.py %s -o song.json --name <歌名> --song-id <未占用编号>"
          % os.path.basename(a.midi))
    print("         python3 scripts/make_datapack.py song.json -o out/<歌名> --mc-version <版本>   # 或 generate.py + validate_pack.py")

    if a.json:
        rep["verdict"] = {"voices": voices, "quantized_ticks": len(ticks)}
        rep["ticks_after_quantize"] = len(ticks)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print("\n结构化结果 → %s" % a.json)


if __name__ == "__main__":
    main()
