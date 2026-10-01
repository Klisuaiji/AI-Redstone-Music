#!/usr/bin/env python3
# song.json → lemon 风格 mcfunction（算法已对 lemon 参考包逆向验证）
import json, os, sys, argparse

INSTRUMENTS = {
    "harp":            {"min": "1.13", "sound": "block.note_block.harp",               "base": 54},
    "bass":            {"min": "1.13", "sound": "block.note_block.bass",               "base": 30},
    "basedrum":        {"min": "1.13", "sound": "block.note_block.basedrum",           "base": 54},
    "snare":           {"min": "1.13", "sound": "block.note_block.snare",              "base": 54},
    "hat":             {"min": "1.13", "sound": "block.note_block.hat",                "base": 54},
    "bell":            {"min": "1.13", "sound": "block.note_block.bell",               "base": 78},
    "flute":           {"min": "1.13", "sound": "block.note_block.flute",              "base": 66},
    "chime":           {"min": "1.13", "sound": "block.note_block.chime",              "base": 78},
    "guitar":          {"min": "1.13", "sound": "block.note_block.guitar",             "base": 42},
    "xylophone":       {"min": "1.13", "sound": "block.note_block.xylophone",          "base": 78},
    "iron_xylophone":  {"min": "1.14", "sound": "block.note_block.iron_xylophone",     "base": 54},
    "cow_bell":        {"min": "1.14", "sound": "block.note_block.cow_bell",           "base": 54},
    "didgeridoo":      {"min": "1.14", "sound": "block.note_block.didgeridoo",         "base": 30},
    "bit":             {"min": "1.14", "sound": "block.note_block.bit",                "base": 54},
    "banjo":           {"min": "1.14", "sound": "block.note_block.banjo",              "base": 54},
    "pling":           {"min": "1.14", "sound": "block.note_block.pling",              "base": 54},
    "skeleton":        {"min": "1.20", "sound": "block.note_block.imitate.skeleton",        "base": 54},
    "wither_skeleton": {"min": "1.20", "sound": "block.note_block.imitate.wither_skeleton", "base": 54},
    "zombie":          {"min": "1.20", "sound": "block.note_block.imitate.zombie",          "base": 54},
    "creeper":         {"min": "1.20", "sound": "block.note_block.imitate.creeper",         "base": 54},
    "piglin":          {"min": "1.20", "sound": "block.note_block.imitate.piglin",          "base": 54},
    "dragon":          {"min": "1.20", "sound": "block.note_block.imitate.ender_dragon",    "base": 54},
    "trumpet":         {"min": "26.1", "sound": "block.note_block.trumpet",           "base": 54},
    "trumpet_exposed": {"min": "26.1", "sound": "block.note_block.trumpet_exposed",   "base": 54},
    "trumpet_weathered":{"min": "26.1","sound": "block.note_block.trumpet_weathered", "base": 42},
    "trumpet_oxidized":{"min": "26.1", "sound": "block.note_block.trumpet_oxidized",  "base": 42},
}
HEADS = ("skeleton","wither_skeleton","zombie","creeper","piglin","dragon")

def vt(v): return tuple(int(x) for x in v.split("."))
def pitch_of(uc): return 2 ** ((uc - 12) / 12.0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file"); ap.add_argument("-o","--out",required=True)
    ap.add_argument("--speed",type=int,default=None)
    ap.add_argument("--style",choices=["lemon","standalone"],default=None)
    a = ap.parse_args()
    song = json.load(open(a.json_file, encoding="utf-8"))
    m = song["meta"]
    speed = a.speed if a.speed is not None else m.get("speed", 2)
    style = a.style or m.get("style", "lemon")
    ns = m.get("namespace","minecraft")
    path = m.get("path","music/"+m.get("name","song"))
    sid = m.get("song_id",1); tag = m.get("mute_tag","no_music")
    nxt = m.get("next_song"); ver = m.get("mc_version","1.21")
    unit = m.get("time_unit","nbs_ticks"); tps = m.get("tempo_tps",10)
    scale = {"nbs_ticks": 20.0/tps*speed, "game_ticks": float(speed)}.get(unit, 1.0)

    events, warns = {}, []
    for tr in song["tracks"]:
        if tr.get("include", True) is False: continue
        dinst = tr.get("instrument_default","harp")
        for n in tr["notes"]:
            raw = n["t"]*scale; t = round(raw)
            if abs(raw-t) > 1e-6:
                sys.exit("时间 %s 换算非整数(%s)，请调整 tempo/speed 或量化" % (n["t"], raw))
            inst = n.get("inst", dinst)
            if inst not in INSTRUMENTS: sys.exit("未知乐器: "+inst)
            if vt(ver) < vt(INSTRUMENTS[inst]["min"]):
                sys.exit("乐器 %s 需 MC %s+（目标 %s）" % (inst, INSTRUMENTS[inst]["min"], ver))
            uc = n["midi"] - INSTRUMENTS[inst]["base"]
            if not 0 <= uc <= 24:
                warns.append("t=%s %s 音域外(uc=%d)已夹取" % (n["t"], inst, uc)); uc = min(24,max(0,uc))
            if inst in HEADS: warns.append("t=%s 头颅乐器无视pitch" % n["t"])
            events.setdefault(t,[]).append((INSTRUMENTS[inst]["sound"], "%.6f"%pitch_of(uc), n.get("vol",1.0)))
    if not events: sys.exit("没有音符！")

    ticks = sorted(events); maxt = ticks[-1]
    N = 1
    while N <= maxt: N *= 2
    root = "0_%d" % (N-1)
    ntset = set(ticks); tree = {}
    def build(x, y):
        rng = [t for t in ntset if x <= t <= y]
        if not rng: return None
        name = "%d_%d" % (x, y)
        # 叶子必须 1 格宽（y == x，详见 references/format_spec.md §A）。
        # 若写成 y-x<=1，叶子只输出 rng[0]；而二分出的最深层叶子恒为对齐的 [2k,2k+1]，
        # 于是相邻 tick 对 (2k,2k+1) 同时有音符时，2k+1 的 notes/<t>.mcfunction 会生成
        # 却没有任何节点调用它 → 该音符永久静音（实测某曲 1169 个 notes 里 79 个不可达）。
        if y == x:  # 叶子
            t = rng[0]; guard = "-1" if t == 0 else str(t-1)
            tree[name] = ("execute if score music_progress nbs_s matches %d..%d "
                          "if score music_progress nbs_t matches ..%s run function %s:%s/notes/%d"
                          % (80*x, 80*y+160, guard, ns, path, t))
            return name
        mid = (x+y)//2; lines = []
        L = build(x, mid)
        if L: lines.append("execute if score music_progress nbs_s matches %d..%d run function %s:%s/tree/%s"
                           % (80*x, 80*(mid+3), ns, path, L))
        R = build(mid+1, y)
        if R: lines.append("execute if score music_progress nbs_s matches %d..%d run function %s:%s/tree/%s"
                           % (80*(mid+1), 80*(y+4), ns, path, R))
        tree[name] = "\r\n".join(lines); return name
    build(0, N-1)

    os.makedirs(os.path.join(a.out,"notes"), exist_ok=True)
    os.makedirs(os.path.join(a.out,"tree"), exist_ok=True)
    for t in ticks:
        lines = ["execute as @a[tag=!%s] at @s run playsound minecraft:%s voice @s ^0 ^ ^ %g %s 1"
                 % (tag, s, v, p) for (s,p,v) in events[t]]
        if t == maxt and m.get("auto_stop", True):
            lines.append("function %s:%s/stop" % (ns, path))
        else:
            lines.append("scoreboard players set music_progress nbs_t %d" % t)
        open(os.path.join(a.out,"notes","%d.mcfunction"%t),"w",encoding="utf-8",newline="").write("\r\n".join(lines)+"\r\n")
    for name, c in tree.items():
        open(os.path.join(a.out,"tree",name+".mcfunction"),"w",encoding="utf-8",newline="").write(c+"\r\n")
    def w(fn, txt): open(os.path.join(a.out,fn),"w",encoding="utf-8",newline="").write(txt.replace("\n","\r\n"))
    w("play.mcfunction", "scoreboard players set music_progress music_type %d\nscoreboard players set music_progress nbs_s 0\nscoreboard players set music_progress nbs_t -1\n" % sid)
    w("stop.mcfunction", "scoreboard players set music_progress nbs_s 0\nscoreboard players reset music_progress nbs_t\n" + (("function %s\n"%nxt) if nxt else ""))
    w("tick.mcfunction", "execute if score music_progress music_type matches %d run scoreboard players operation music_progress nbs_s += #speed nbs_s\nexecute if score music_progress music_type matches %d run function %s:%s/tree/%s\n" % (sid, sid, ns, path, root))
    if style == "standalone":
        w("_standalone_init.mcfunction", "scoreboard objectives add music_type dummy\nscoreboard objectives add nbs_s dummy\nscoreboard objectives add nbs_t dummy\nscoreboard players set #speed nbs_s %d\n" % speed)
        w("_standalone_tick.mcfunction", "function %s:%s/tick\n" % (ns, path))
    for x in warns: print("WARN:", x, file=sys.stderr)
    print("OK: %d 音符tick / %d 树节点 / 根 %s → %s" % (len(ticks), len(tree), root, a.out))

if __name__ == "__main__": main()
