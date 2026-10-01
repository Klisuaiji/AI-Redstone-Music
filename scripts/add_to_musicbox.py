#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把歌曲注册进「红石音乐盒」通用数据包（或从盒子里移除）。

歌曲遵循本 skill 的时轴约定（music_type / nbs_s / nbs_t + #speed 80），
所以盒子只负责"选曲 + 派发"，歌曲本体由 generate.py 生成。

用法：
    # 从 song.json 注册（自动分配编号）
    python3 scripts/add_to_musicbox.py --box out/musicbox --song song.json --name "反乌托邦"
    # 直接从 MIDI 一步到位（内部先跑 midi_to_song.py）
    python3 scripts/add_to_musicbox.py --box out/musicbox --song 歌曲.mid --name "Lemon" --lrc 歌词.lrc
    # 指定编号 / 移除 / 查看
    python3 scripts/add_to_musicbox.py --box out/musicbox --song song.json --id 3
    python3 scripts/add_to_musicbox.py --box out/musicbox --remove 3
    python3 scripts/add_to_musicbox.py --box out/musicbox --list

注册后需要 /reload 才会生效（新增的是新的函数文件）。
仅用标准库。
"""
import argparse, json, os, re, shutil, subprocess, sys

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATE = os.path.join(HERE, "generate.py")
MIDI2SONG = os.path.join(HERE, "midi_to_song.py")
MANIFEST = "musicbox_songs.json"
SONG_DIR = "data/rmb/function/song"


# --------------------------------------------------------------------------- LRC
def parse_lrc(path):
    """[mm:ss.xx]文本 → [(秒, 文本), ...]（同一行有多个时间戳就展开成多条）"""
    out = []
    for raw in open(path, encoding="utf-8-sig", errors="replace").read().splitlines():
        stamps = re.findall(r"\[(\d+):(\d+(?:[.:]\d+)?)\]", raw)
        text = re.sub(r"\[\d+:[\d.:]+\]", "", raw).strip()
        if not stamps:
            continue
        for mm, ss in stamps:
            sec = int(mm) * 60 + float(ss.replace(":", "."))
            if text:
                out.append((sec, text))
    out.sort(key=lambda x: x[0])
    return out


def lrc_function(song_id, lines, tick_rate=20):
    """歌词函数：用 nbs_s 当时间轴（每刻都推进，暂停/禁播时也跟着停）"""
    L = ["# 歌词 —— 由 scripts/add_to_musicbox.py 生成（时间轴用 nbs_s）",
         "execute unless score music_progress music_type matches %d run return 0" % song_id]
    if not lines:
        L.append("# 这首歌没有歌词")
        return "\n".join(L)
    for i, (sec, text) in enumerate(lines):
        a = int(round(sec * tick_rate))
        # 记分板是 32 位整数：nbs_s 的上界不能写到 2147483647 以上
        b = int(round(lines[i + 1][0] * tick_rate)) if i + 1 < len(lines) else 2147483647 // 80
        if b <= a:
            b = a + 1
        L.append('execute if score music_progress nbs_s matches %d..%d run title @s actionbar %s'
                 % (a * 80, min(b * 80 - 1, 2147483647), json.dumps({"text": text}, ensure_ascii=False)))
    return "\n".join(L)


# --------------------------------------------------------------------------- 写入
def w(path, text, crlf=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if crlf:
        text = text.replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text if text.endswith("\n") else text + "\n")


def load_manifest(box):
    p = os.path.join(box, MANIFEST)
    if os.path.isfile(p):
        return json.load(open(p, encoding="utf-8"))
    return []


def save_manifest(box, songs):
    songs = sorted(songs, key=lambda s: s["id"])
    with open(os.path.join(box, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=1)
    return songs


def regenerate_registry(box, songs):
    """重新生成 max / name / by_name / menu_list 四个文件。"""
    mx = max([s["id"] for s in songs], default=0)

    w(os.path.join(box, SONG_DIR, "max.mcfunction"),
      "# 曲目数量 —— 由 scripts/add_to_musicbox.py 自动生成，不要手改\n"
      "scoreboard players set #max mb_cfg %d" % mx, crlf=True)

    L = ["# 当前曲目名字幕 —— 由 scripts/add_to_musicbox.py 自动生成，不要手改"]
    for s in songs:
        L.append('execute if score music_progress music_type matches %d run title @a actionbar %s'
                 % (s["id"], json.dumps({"text": "♪ 正在播放：" + s["name"]}, ensure_ascii=False)))
    L.append("scoreboard players set @a mb_msg 40")
    w(os.path.join(box, SONG_DIR, "name.mcfunction"), "\n".join(L), crlf=True)

    L = ["# 歌名 → 编号 —— 由 scripts/add_to_musicbox.py 自动生成，不要手改"]
    for s in songs:
        L.append('execute if data storage rmb:io arg{song:%s} run scoreboard players set #cur mb_cfg %d'
                 % (json.dumps(s["name"], ensure_ascii=False), s["id"]))
    w(os.path.join(box, SONG_DIR, "by_name.mcfunction"), "\n".join(L), crlf=True)

    L = ["# 点歌菜单列表 —— 由 scripts/add_to_musicbox.py 自动生成，不要手改"]
    if not songs:
        L += ['tellraw @s ["",{"text":"[音乐盒] ","color":"gold"},{"text":"还没有添加歌曲。","color":"yellow"}]',
              'tellraw @s ["",{"text":"  用 ","color":"gray"},{"text":"python3 scripts/add_to_musicbox.py --box <数据包> --song song.json","color":"white"},{"text":" 注册","color":"gray"}]']
    for s in songs:
        L.append("tellraw @s " + json.dumps(["", {"text": "[%d] " % s["id"], "color": "gray"},
                                             {"text": s["name"], "color": "white",
                                              "clickEvent": {"action": "run_command",
                                                             "value": "/trigger play set %d" % s["id"]},
                                              "hoverEvent": {"action": "show_text",
                                                             "value": "点击播放 " + s["name"]}}],
                                            ensure_ascii=False))
    if songs:
        L.append('tellraw @s ["",{"text":"共 %d 首；也可 /function rmb:play {song:\\"歌名\\"} 按名字点歌","color":"dark_gray"}]' % len(songs))
    w(os.path.join(box, "data/rmb/function/box/menu_list.mcfunction"), "\n".join(L), crlf=True)


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="把歌曲注册进红石音乐盒数据包")
    ap.add_argument("--box", required=True, help="音乐盒数据包目录（含 pack.mcmeta 的那个）")
    ap.add_argument("--song", default=None, help="song.json 或 .mid（.mid 会先自动编曲）")
    ap.add_argument("--name", default=None, help="菜单里显示的歌名（默认取 song.json 的 meta.name）")
    ap.add_argument("--id", type=int, default=None, help="指定曲目编号（默认自动分配下一个）")
    ap.add_argument("--lrc", default=None, help="歌词文件（LRC 格式，可选）")
    ap.add_argument("--mc-version", default="26.2", help="从 .mid 编曲时的目标版本")
    ap.add_argument("--song-id-conflict", action="store_true", help="允许覆盖已存在的编号")
    ap.add_argument("--remove", type=int, default=None, help="移除某个编号的歌曲")
    ap.add_argument("--list", action="store_true", help="只列出已注册歌曲")
    a = ap.parse_args()

    box = os.path.abspath(a.box)
    if not os.path.isfile(os.path.join(box, "pack.mcmeta")):
        sys.exit("--box %s 看起来不是数据包目录（缺少 pack.mcmeta）" % box)
    songs = load_manifest(box)

    if a.list:
        print("已注册 %d 首：" % len(songs))
        for s in songs:
            print("  [%d] %s" % (s["id"], s["name"]))
        print("曲目数量 #max = %d" % max([s["id"] for s in songs], default=0))
        return 0

    if a.remove is not None:
        hit = [s for s in songs if s["id"] == a.remove]
        if not hit:
            sys.exit("没有编号 %d 的歌曲" % a.remove)
        songs = [s for s in songs if s["id"] != a.remove]
        d = os.path.join(box, SONG_DIR, str(a.remove))
        if os.path.isdir(d):
            shutil.rmtree(d)
        regenerate_registry(box, save_manifest(box, songs))
        print("已移除 [%d] %s（记得 /reload；注意编号不会自动补位，用 --id 可以填洞）"
              % (a.remove, hit[0]["name"]))
        return 0

    if not a.song:
        sys.exit("需要 --song（song.json 或 .mid），或 --list / --remove")

    # ---- 1. 准备 song.json ----
    src = os.path.abspath(a.song)
    tmp_song = None
    if src.lower().endswith((".mid", ".midi")):
        tmp_song = os.path.join(box, ".import.song.json")
        name = a.name or os.path.splitext(os.path.basename(src))[0]
        cmd = [sys.executable, MIDI2SONG, src, "-o", tmp_song, "--name", re.sub(r"[^0-9a-zA-Z_]+", "_", name).lower(),
               "--namespace", "rmb", "--mc-version", a.mc_version]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            sys.stdout.buffer.write(r.stdout)
            sys.stdout.buffer.flush()
        except Exception:
            pass
        if r.returncode != 0:
            sys.exit("midi_to_song.py 失败")
        song_path = tmp_song
    else:
        song_path = src
    song = json.load(open(song_path, encoding="utf-8"))

    # ---- 2. 决定编号 ----
    name = a.name or song.get("meta", {}).get("name") or "未命名"
    if a.id is not None:
        sid = a.id
    else:
        sid = max([s["id"] for s in songs], default=0) + 1
    if any(s["id"] == sid for s in songs) and not a.song_id_conflict:
        sys.exit("编号 %d 已被 [%s] 占用；换一个 --id，或加 --song-id-conflict 覆盖"
                 % (sid, [s["name"] for s in songs if s["id"] == sid][0]))
    if sid < 1:
        sys.exit("编号必须 ≥ 1")

    # ---- 3. 改写 meta 并生成歌曲函数 ----
    song.setdefault("meta", {})
    song["meta"].update({
        "namespace": "rmb",
        "path": "song/%d" % sid,
        "song_id": sid,
        "style": "lemon",              # 不要 _standalone_* 辅助文件，盒子负责 init
        "next_song": "rmb:song/ended",  # 播完自动下一首
        "time_unit": song["meta"].get("time_unit", "nbs_s_units"),
        "speed": 80,
        "auto_stop": True,
    })
    out_dir = os.path.join(box, SONG_DIR, str(sid))
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    w(os.path.join(box, ".build.song.json"), json.dumps(song, ensure_ascii=False))
    cmd = [sys.executable, GENERATE, os.path.join(box, ".build.song.json"), "-o", out_dir, "--speed", "80"]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        sys.stdout.buffer.write(r.stdout)
        sys.stdout.buffer.flush()
    except Exception:
        pass
    if r.returncode != 0:
        sys.exit("generate.py 失败")

    # ---- 4. 歌词 ----
    lines = parse_lrc(a.lrc) if a.lrc else []
    w(os.path.join(out_dir, "lrc.mcfunction"), lrc_function(sid, lines), crlf=True)

    # ---- 5. 更新清单与注册表 ----
    songs = [s for s in songs if s["id"] != sid]
    songs.append({"id": sid, "name": name, "notes": sum(len(t["notes"]) for t in song.get("tracks", []))})
    regenerate_registry(box, save_manifest(box, songs))

    for junk in (".import.song.json", ".build.song.json"):
        p = os.path.join(box, junk)
        if os.path.isfile(p):
            os.remove(p)

    print("已注册 [%d] %s → %s" % (sid, name, os.path.relpath(out_dir, box).replace(os.sep, "/")))
    if lines:
        print("  歌词：%d 句（用 /trigger lrc 开关）" % len(lines))
    print("  曲目总数 #max = %d" % max(s["id"] for s in songs))
    print("  进游戏执行 /reload 后生效；菜单：/trigger menu → 双击右键")
    return 0


if __name__ == "__main__":
    sys.exit(main())
