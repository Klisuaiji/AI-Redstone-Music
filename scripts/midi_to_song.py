#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MIDI → song.json（自动编曲 + 编曲决策报告）。

把 SKILL.md 第三、四步里"人工判断"的部分做成可复现的规则：
轨道分类 → 乐器映射 → 音量表 → 时轴量化 → 音域折叠 → 去重 → 写 song.json（+ 报告）。

时轴默认按**已验证的约定**输出：`time_unit=nbs_s_units` + `speed=80`，
即 song.json 里的 t 就是游戏 tick（宿主 `#speed nbs_s 80`、树窗口 80×t）。
`--speed` 换成别的值时，会按 t = round(游戏tick × S/80) 重标时间轴并警告分辨率损失。

用法：
    python3 scripts/midi_to_song.py 歌曲.mid -o song.json --name m3 --song-id 9 \\
        --mc-version 26.2 --lead-split 72 --lead-inst flute --report 编曲说明.md

随后：
    python3 scripts/generate.py song.json -o out/music/m3
    python3 scripts/validate_pack.py --pack out --namespace minecraft --song m3 --song-id 9 --speed 80
仅用标准库（generate.py 的乐器表被复用，保证与校验口径一致）。
"""
import argparse, collections, json, os, re, sys

try:            # Windows 控制台默认 GBK：让非 GBK 字符（⚠ 等）降级为 ?，而不是直接抛异常
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from midilib import read_midi, gm_drum_name
from generate import INSTRUMENTS, HEADS

# 默认混音音量（references/midi_notes.md 第 6 节，经用户听感校准）
DEFAULT_VOL = {"basedrum": 0.6, "snare": 0.5, "hat": 0.25, "bit": 0.5}
DRUM_KEYWORDS = ("drum", "perc", "beat", "鼓", "打击")
BASS_KEYWORDS = ("bass", "贝斯", "贝司", "低音")


def vol_of(inst, overrides):
    if inst in overrides:
        return overrides[inst]
    return DEFAULT_VOL.get(inst, 1.0)


def vtuple(v):
    return tuple(int(x) for x in str(v).split("."))


def sanitize(name):
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", name).strip("_").lower()
    return s or "song"


def main():
    ap = argparse.ArgumentParser(description="MIDI → song.json（自动编曲）")
    ap.add_argument("midi")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--name", default=None, help="歌名（路径用，默认取文件名）")
    ap.add_argument("--namespace", default="minecraft")
    ap.add_argument("--path", default=None, help="函数路径，默认 music/<name>")
    ap.add_argument("--song-id", type=int, default=8)
    ap.add_argument("--mc-version", default="26.2")
    ap.add_argument("--speed", type=int, default=80, help="#speed nbs_s（默认 80 = t 即游戏 tick）")
    ap.add_argument("--tick-rate", type=int, default=20,
                    help="宿主 tick rate：20=原版（网格 50ms）；80 可把时间网格细化到 12.5ms（需 MC 1.20.3+ 且手动 /tick rate 80）")
    ap.add_argument("--style", choices=["lemon", "standalone"], default="standalone")
    ap.add_argument("--lead-split", type=int, default=72, help="该音高以上算主旋律（默认 72）")
    ap.add_argument("--lead-inst", default="auto",
                    help="主旋律乐器；auto（默认）= 整轨塞得进单一乐器就用它，否则按 --lead-split 拆分")
    ap.add_argument("--chord-inst", default="guitar")
    ap.add_argument("--bass-inst", default="bass")
    ap.add_argument("--assign", action="append", default=[], metavar="PAT=INST",
                    help="轨道名含 PAT（不区分大小写）时强制用 INST，可重复")
    ap.add_argument("--skip", action="append", default=[], metavar="PAT", help="跳过匹配的轨道，可重复")
    ap.add_argument("--vol", action="append", default=[], metavar="INST=VOL", help="覆盖默认音量，可重复")
    ap.add_argument("--drum-map", default="36=basedrum,38=snare,40=snare",
                    help="GM 音高→乐器，未列出的走 hat（默认 36=basedrum,38=snare,40=snare）")
    ap.add_argument("--no-fold", action="store_true", help="不做八度折叠（交给 generate.py 夹取并告警）")
    ap.add_argument("--force", action="store_true", help="即使 #speed 的时间分辨率不可用也照做")
    ap.add_argument("--report", default=None, help="把编曲决策报告写成 markdown")
    a = ap.parse_args()

    # 时间分辨率：宿主每刻 nbs_s += #speed，树窗口 80×t，故 note t 在游戏 tick 80t/#speed 发声；
    # 而 1 游戏 tick = 1/tick_rate 秒，所以 1 个 t 单位 = 80/(#speed × tick_rate) 秒。
    # 只有 #speed=80 时 t 才等于游戏 tick；tick_rate 越大网格越细（20→50ms，80→12.5ms）。
    R = a.tick_rate
    res_ms = 80000.0 / (a.speed * R)
    if res_ms > 100.0 and not a.force:
        sys.exit("#speed %d + tick_rate %d 的时间分辨率是 1 个 t = %.0f ms（%.2f 秒一格），"
                 "会把整首歌量化成糊状，实际不可用。\n"
                 "  宿主每刻 nbs_s += #speed（树窗口 80×t），1 游戏 tick = 1/tick_rate 秒；\n"
                 "  默认 #speed 80 + tick_rate 20 → t 就是游戏 tick（50 ms）。确实要用请加 --force。"
                 % (a.speed, R, res_ms, res_ms / 1000.0))
    if R not in (20, 80) and res_ms < 50.0:
        print("提示: tick_rate %d 的网格是 %.2f ms；请确认宿主真的执行了 /tick rate %d" % (R, res_ms, R))

    for inst in (a.chord_inst, a.bass_inst) + (() if a.lead_inst == "auto" else (a.lead_inst,)):
        if inst not in INSTRUMENTS:
            sys.exit("未知乐器: %s（白名单见 references/instruments.md）" % inst)
        if inst in HEADS:
            sys.exit("头颅乐器没有音高概念，不能用于旋律: %s" % inst)
        if vtuple(a.mc_version) < vtuple(INSTRUMENTS[inst]["min"]):
            sys.exit("乐器 %s 需要 MC %s+（目标 %s）" % (inst, INSTRUMENTS[inst]["min"], a.mc_version))

    drum_map = {}
    for kv in a.drum_map.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            drum_map[int(k.strip())] = v.strip()
    assigns = []
    for kv in a.assign:
        if "=" not in kv:
            sys.exit("--assign 需要 PAT=INST 形式: %s" % kv)
        p, i = kv.split("=", 1)
        if i.strip() not in INSTRUMENTS:
            sys.exit("未知乐器: %s" % i)
        assigns.append((p.strip().lower(), i.strip()))
    vovers = {}
    for kv in a.vol:
        if "=" in kv:
            k, v = kv.split("=", 1)
            vovers[k.strip()] = float(v)

    name = sanitize(a.name or os.path.splitext(os.path.basename(a.midi))[0])
    path = a.path or ("music/" + name)
    m = read_midi(a.midi)
    bpm = m.bpm_at(0)
    tps_midi = m.ticks_per_second(0)

    def game_tick_of(midi_tick):
        return m.sec_at(midi_tick) * R

    # 宿主每刻 nbs_s += S，树窗口 80t → note t 在游戏 tick 80t/S 发声；
    # 1 游戏 tick = 1/R 秒 → 要让音符落在「秒」上，t = 秒 × R × S / 80
    def to_t(midi_tick):
        g = game_tick_of(midi_tick)
        return int(round(g * a.speed / 80.0)), g

    events = collections.defaultdict(dict)          # t -> (inst, midi) -> vol
    stats = collections.Counter()
    errs, folds = [], collections.Counter()
    mapping_rows = []
    tick_src = {}                                   # t -> 第一个落在这个 t 的 MIDI tick（用于抽查表）

    def add(midi_tick, inst, midi, vol, tag):
        t, g = to_t(midi_tick)
        base = INSTRUMENTS[inst]["base"]
        lo, hi = base, base + 24
        n = 0
        if not a.no_fold:
            while midi > hi:
                midi -= 12
                n -= 1
            while midi < lo:
                midi += 12
                n += 1
        if n:
            stats["folded_" + inst] += 1
            folds[n] += 1
        key = (inst, midi)
        if key in events[t]:
            stats["dupe_dropped"] += 1
            return
        if t < 0:
            stats["dropped_negative_t"] += 1
            return
        events[t][key] = vol
        tick_src.setdefault(t, midi_tick)
        stats["notes_" + tag] += 1
        errs.append(abs(80.0 * t / a.speed - g) / R * 1000.0)   # 实际发声时刻与理想时刻之差（毫秒）

    # ---------------- 轨道分类 ----------------
    used_tracks = []
    for tr in m.tracks:
        if not tr.notes:
            continue
        low = tr.name.lower()
        if any(k.lower() in low for k in a.skip):
            mapping_rows.append((tr, "—", "被 --skip 跳过", 0, 0, "-"))
            continue
        forced = next((i for p, i in assigns if p in low), None)
        is_drum = (9 in tr.channels) or any(k in low for k in DRUM_KEYWORDS)
        is_bass = any(k in low for k in BASS_KEYWORDS)

        if forced:
            inst = forced
            for n in tr.notes:
                add(n.tick, inst, n.pitch, vol_of(inst, vovers), "assigned")
            mapping_rows.append((tr, inst, "--assign 指定", len(tr.notes),
                                 stats["folded_" + inst], vol_of(inst, vovers)))
        elif is_drum:
            cnt = collections.Counter()
            for n in tr.notes:
                inst = drum_map.get(n.pitch, "hat")
                if inst not in INSTRUMENTS:
                    sys.exit("--drum-map 里的未知乐器: %s" % inst)
                add(n.tick, inst, 54, vol_of(inst, vovers), "drum")
                cnt[inst] += 1
            mapping_rows.append((tr, "鼓组" + str(dict(cnt)), "声道 9 / 轨道名含鼓关键词",
                                 len(tr.notes), 0, "见音量表"))
        elif is_bass:
            inst = a.bass_inst
            for n in tr.notes:
                add(n.tick, inst, n.pitch, vol_of(inst, vovers), "bass")
            mapping_rows.append((tr, inst, "轨道名含 bass/低音关键词", len(tr.notes),
                                 stats["folded_" + inst], vol_of(inst, vovers)))
        else:
            ps = [n.pitch for n in tr.notes]
            lead_inst = a.lead_inst
            picked = None
            if lead_inst == "auto":
                # 整轨音域塞得进单一乐器就不拆（25 个半音以内），按偏好顺序取第一个装得下的
                for cand in ("pling", "flute", "bit", "harp", "bell", "chime"):
                    lo_, hi_ = INSTRUMENTS[cand]["base"], INSTRUMENTS[cand]["base"] + 24
                    if min(ps) >= lo_ and max(ps) <= hi_:
                        picked = cand
                        break
            if picked:
                for n in tr.notes:
                    add(n.tick, picked, n.pitch, vol_of(picked, vovers), "lead")
                mapping_rows.append((tr, picked, "整轨音域 %d..%d 塞得进单一乐器（auto）"
                                     % (min(ps), max(ps)), len(tr.notes), stats["folded_" + picked],
                                     vol_of(picked, vovers)))
            else:
                # 拆主旋律/和弦；auto 时为高音声部挑折八度最少的乐器
                hi_inst = lead_inst
                if hi_inst == "auto":
                    hi = [p for p in ps if p >= a.lead_split] or [max(ps)]
                    best, bestn = "flute", None
                    for cand in ("flute", "pling", "bit", "harp", "bell"):
                        lo_, hh_ = INSTRUMENTS[cand]["base"], INSTRUMENTS[cand]["base"] + 24
                        n_fold = sum(1 for p in hi if not (lo_ <= p <= hh_))
                        if bestn is None or n_fold < bestn:
                            best, bestn = cand, n_fold
                    hi_inst = best
                lead = chord = 0
                for n in tr.notes:
                    if n.pitch >= a.lead_split:
                        add(n.tick, hi_inst, n.pitch, vol_of(hi_inst, vovers), "lead")
                        lead += 1
                    else:
                        add(n.tick, a.chord_inst, n.pitch, vol_of(a.chord_inst, vovers), "chord")
                        chord += 1
                mapping_rows.append((tr, "%s + %s" % (hi_inst, a.chord_inst),
                                     "按音高 %d 拆分（>=%d 主旋律 %d 音 / 其余 %d 音）"
                                     % (a.lead_split, a.lead_split, lead, chord),
                                     len(tr.notes), stats["folded_" + hi_inst] + stats["folded_" + a.chord_inst],
                                     "%s / %s" % (vol_of(hi_inst, vovers), vol_of(a.chord_inst, vovers))))
        used_tracks.append(tr)

    if not events:
        sys.exit("没有产出任何音符")

    ticks = sorted(events)
    maxt = ticks[-1]
    poly = max(len(v) for v in events.values())

    # ---------------- 写 song.json ----------------
    # 轨道顺序：先按偏好排（去重！），再兜底把实际用到但没列进偏好的乐器补上（避免漏轨）
    pref = []
    for x in [a.lead_inst, a.chord_inst, a.bass_inst, "basedrum", "snare", "hat",
              "pling", "bit", "harp", "bell", "chime", "xylophone", "banjo",
              "iron_xylophone", "cow_bell", "didgeridoo", "flute", "guitar"]:
        if x != "auto" and x not in pref:
            pref.append(x)
    used = set(i for v in events.values() for (i, _m) in v)
    order = [i for i in pref if i in used] + sorted(used - set(pref))
    tracks = []
    for inst in order:
        notes = [{"t": t, "midi": mid, "vol": v}
                 for t in ticks for (i, mid), v in sorted(events[t].items()) if i == inst]
        if notes:
            tracks.append({"name": inst if inst not in ("basedrum", "snare", "hat") else "drums_" + inst,
                           "include": True, "instrument_default": inst, "notes": notes})
    song = {"meta": {
        "name": name, "namespace": a.namespace, "path": path, "song_id": a.song_id,
        "mc_version": a.mc_version, "style": a.style, "time_unit": "nbs_s_units",
        "speed": a.speed, "auto_stop": True, "next_song": None, "mute_tag": "no_music",
        "_source": os.path.basename(a.midi),
        "_timeline": "t = 游戏 tick（1/%d 秒）；宿主 #speed nbs_s = %d；树窗口 80*t" % (R, a.speed),
        "_tick_rate": R},
        "tracks": tracks}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(song, f, ensure_ascii=False)
    total = sum(len(t["notes"]) for t in tracks)

    errs.sort()
    print("song.json → %s" % a.out)
    print("  源: %s  %.3f BPM  时长 %.2fs  原始 note-on %d" % (os.path.basename(a.midi), bpm,
                                                              m.sec_at(m.last_note_tick()), m.note_count))
    print("  产出: %d 个音符 / %d 个音符 tick / 末 tick %d (%.1fs) / 同刻最多 %d 个 playsound"
          % (total, len(ticks), maxt, maxt / float(R), poly))
    print("  时轴: tick_rate=%d（1 个 t = %.2f ms）  t = round(秒 × %d × %d/80) = round(秒 × %.4g)"
          % (R, res_ms, R, a.speed, R * a.speed / 80.0))
    print("  量化误差: 中位 %.1f ms / p90 %.1f ms / 最大 %.1f ms"
          % (errs[len(errs) // 2], errs[int(len(errs) * 0.9)], errs[-1]))
    for k in sorted(stats):
        print("    %-20s %d" % (k, stats[k]))
    if folds:
        print("  八度折叠: %s（+1 = 升高一个八度以进入乐器音域）"
              % ", ".join("%+d×%d" % (k, v) for k, v in sorted(folds.items())))
    if a.speed != 80 or R != 20:
        print("  ⚠ 宿主必须满足: #speed nbs_s = %d（init.mcfunction 已写）%s"
              % (a.speed, "，且进游戏后手动执行 /tick rate %d（重进世界会重置）" % R if R != 20 else ""))

    # ---------------- 编曲决策报告 ----------------
    if a.report:
        L = []
        L.append("# 编曲决策说明（由 midi_to_song.py 生成）\n")
        L.append("## 源\n")
        L.append("- 文件：`%s`" % os.path.basename(a.midi))
        L.append("- 速度：**%.3f BPM**；division %d ticks/四分音符；时长 %.2f s" % (bpm, m.division, m.sec_at(m.last_note_tick())))
        L.append("- 原始 note-on：%d（只数 note-on，不做 on/off 配对）" % m.note_count)
        L.append("- 速度变化：%s\n" % ("单一速度" if len(m.tempos) == 1 else
                                      " | ".join("%.3f BPM @%d" % (60e6 / u, t) for t, u in m.tempos)))
        L.append("## 声部映射\n")
        L.append("| 轨道 | 声道 | 原始音符 | 映射到 | 判据 | 音量 | 八度折叠 |")
        L.append("|---|---|---|---|---|---|---|")
        for tr, inst, why, cnt, foldn, vol in mapping_rows:
            L.append("| %s | %s | %d | %s | %s | %s | %d |"
                     % (tr.name, ",".join(str(c) for c in sorted(tr.channels)) or "-", cnt,
                        inst, why, vol, foldn))
        L.append("")
        L.append("## 产出\n")
        L.append("- 音符数 %d，音符 tick %d，末 tick %d（%.1f 秒），同刻最多 %d 个 playsound（上限 255）"
                 % (total, len(ticks), maxt, maxt / float(R), poly))
        L.append("- 去重键 = (tick, 乐器, 音高)：同 tick 同乐器的和弦**全部保留**；本次丢弃重复 %d 个"
                 % stats["dupe_dropped"])
        L.append("- 音域折叠：%s\n" % (", ".join("%+d 个八度 ×%d 个音" % (k, v) for k, v in sorted(folds.items()))
                                      or "无（全部音原本就在乐器音域内）"))
        L.append("## 时轴\n")
        L.append("- `time_unit = nbs_s_units`，`speed = %d`，宿主 `tick_rate = %d`" % (a.speed, R))
        L.append("- 1 个 t 单位 = 80/(#speed × tick_rate) = **%.2f ms**；t = round(秒 × %d × %d/80)"
                 % (res_ms, R, a.speed))
        L.append("- 本次量化误差 中位 %.1f ms / 最大 %.1f ms" % (errs[len(errs) // 2], errs[-1]))
        L.append("- 1 MIDI tick = %.4f s；1 个 t 单位 = %.1f MIDI tick" % (1.0 / tps_midi, tps_midi * res_ms / 1000.0))
        L.append("- 宿主必须满足 `#speed nbs_s = %d`，否则整曲速度不对（树窗口 80×t 与之配套）" % a.speed)
        if R != 20:
            L.append("- ⚠ **进游戏后必须手动执行 `/tick rate %d`**（1.20.3+；退出重进会重置回 20，"
                     "否则整曲会慢 %d 倍）" % (R, R // 20))
        L.append("")
        L.append("## 抽查（最早 8 个音符 tick）\n")
        L.append("| MIDI tick | 秒 | 游戏 tick | 写入 t | 音符 |")
        L.append("|---|---|---|---|---|")
        for t in ticks[:8]:
            mt = tick_src.get(t, 0)
            sec = m.sec_at(mt)
            insts = "+".join(sorted(set(i for i, _ in events[t])))
            L.append("| %d | %.4f | %.2f | %d | %s |" % (mt, sec, sec * 20.0, t, insts))
        L.append("")
        L.append("## 交付前必做\n")
        L.append("```bash")
        L.append("python3 scripts/generate.py %s -o out/%s" % (a.out, path))
        L.append("python3 scripts/validate_pack.py --pack out --namespace %s --song %s --song-id %d --speed %d --mc-version %s"
                 % (a.namespace, name, a.song_id, a.speed, a.mc_version))
        L.append("```")
        with open(a.report, "w", encoding="utf-8") as f:
            f.write("\n".join(L) + "\n")
        print("  编曲决策报告 → %s" % a.report)


if __name__ == "__main__":
    main()
