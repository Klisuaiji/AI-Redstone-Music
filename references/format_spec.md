# lemon 数据包规范（逆向验证）与 song.json 契约

## A. 生成产物规范（与参考包 lemon 逐文件比对）
计分约定：假玩家 `music_progress`；目标 `music_type`(当前歌ID)/`nbs_s`(进度)/`nbs_t`(已播tick)；
每刻 `#speed nbs_s` 加到 nbs_s。所有时间单位为 nbs_s 单位（= NBS tick × 20/tps × speed）。

- play.mcfunction：`music_type=<id>`；`nbs_s=0`；`nbs_t=-1`
- stop.mcfunction：`nbs_s=0`；`reset nbs_t`；可选 `function <next>`（下一首链）
- tick.mcfunction：两行，先 `+= #speed nbs_s` 再调树根，均带 `if music_type matches <id>`
- notes/<t>.mcfunction（CRLF 行尾）：
  `execute as @a[tag=!no_music] at @s run playsound minecraft:<事件> voice @s ^0 ^ ^ <vol> <pitch6位> 1` ×N
  末行 `scoreboard players set music_progress nbs_t <t>`；若 t 是全曲最后 tick：不写 nbs_t，改 `function <ns>:<path>/stop`
- tree/<a>_<b>.mcfunction：覆盖 [0, N-1]，N=2^⌈log2(max+1)⌉
  - 空区间剪枝；b−a≤1 且含音符 → 叶子：`matches 80a..(80b+160)` + `nbs_t matches ..<t-1>`（t=0 时 ..-1）→ notes/<t>
  - 否则 m=(a+b)//2；左孩子窗口 `80a..80(m+3)`，右孩子 `80(m+1)..80(b+4)`（内部节点无 nbs_t 守卫）
  - 单子节点照常输出对应窗口行

## B. song.json Schema
{
  "meta": {
    "name": "lemon",                 // 歌名（英文小写，用于路径）
    "namespace": "minecraft",        // 数据包命名空间
    "path": "music/lemon",           // 函数路径 = namespace:path/...
    "song_id": 8,                    // lemon 兼容模式必填，查重
    "mc_version": "1.20.4",          // 校验乐器白名单
    "style": "lemon",                // lemon | standalone
    "time_unit": "nbs_ticks",        // nbs_ticks | game_ticks | nbs_s_units
    "tempo_tps": 10,                 // NBS 每秒 tick（BPM120/4分音符时值0.5s → tps=2×2=10 的常见推导：tps=BPM/6）
    "speed": 2,                      // 数据包 #speed；nbs_ticks 换算 scale=20/tps*speed
    "auto_stop": true,               // 末 tick 自动接 stop
    "next_song": "minecraft:music/baka/play",  // 可为 null
    "mute_tag": "no_music"
  },
  "tracks": [
    { "name": "vocal_melody", "include": true, "instrument_default": "harp",
      "notes": [ {"t": 0, "midi": 66, "inst": "harp", "vol": 1.0}, ... ] }
  ]
}
字段：t=音符起始（time_unit 单位，必须使 t×scale 为整数）；midi=音高(0-127)；inst 可省略用默认；vol∈(0,1]。
1 个 track 放 1 个声部；人声旋律建议独立 track 便于按用户要求剔除。

## C. nbs_to_json.py 输出说明
解析 .nbs（经典格式优先，自动探测 OpenNBS 新格式）：按 layer 分 track，t=原始 NBS tick，
tempo_tps=文件头 tempo/100，midi=key+33（NBS key 0-87 ↔ F#1-F#7，本工具直接存 key+21 对齐音符盒
MIDI 记法并在 meta 标记 "key_offset":21 由 generate 补偿——实际实现以脚本源码注释为准）。
解析失败时：请用户在 OpenNBS 中另存/导出文本，或改用 MIDI。

## D. 手工生成（无代码环境）备忘
叶子窗口常数：80 为 tick 缩放（=4 单位×20？不——生成器一律按上节公式，勿自行推导）；
pitch 统一 6 位小数；所有行 CRLF；树文件名即区间 "a_b"。
