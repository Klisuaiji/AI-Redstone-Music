# 常用配方

每个配方都是"照着做就能得到结果"的完整流程。工具清单见 `SKILL.md`。

---

## 1. 从 MIDI 到可安装数据包（一条龙）

```bash
python3 scripts/scan_midi.py 歌曲.mid                       # 1. 体检：声部/音域/网格/判定
python3 scripts/midi_to_song.py 歌曲.mid -o song.json \      # 2. 自动编曲 + 决策报告
    --name mysong --song-id 9 --mc-version 26.2 --report 编曲说明.md
python3 scripts/render_preview.py song.json -o preview.wav   # 3. 先听一遍（不用开游戏）
python3 scripts/make_datapack.py song.json -o out/mysong \   # 4. 组装数据包 + zip
    --mc-version 26.2
python3 scripts/validate_pack.py --pack out/mysong \         # 5. 硬门禁
    --namespace minecraft --song mysong --song-id 9 --speed 80 --mc-version 26.2
```

装进存档 `datapacks/` → `/reload` → `/function minecraft:music/mysong/play`。

## 2. 接入已有的 lemon 系宿主数据包

适用：用户已经有一个音乐数据包，每刻执行各曲 `tick`，用 `music_type` 选曲。

1. `midi_to_song.py ... --style lemon`（或生成后不管 `style`，反正只取歌曲文件夹）
2. `python3 scripts/generate.py song.json -o out/music/<歌名>`
3. 把 `out/music/<歌名>/` 整个复制进宿主包 `data/<宿主命名空间>/function/music/` 下
   （1.20.4 及以下用 `functions/`）
4. 三个条件必须与宿主一致，否则整曲静默失效：
   - 宿主的 `#speed nbs_s` 必须 = **80**（`/scoreboard players get #speed nbs_s`）
   - `song_id` 不能与宿主已有曲目冲突（`lemon` 原包占 8）
   - 宿主每刻要执行 `function <ns>:music/<歌名>/tick`
5. **不要**把本曲的 `init.mcfunction`、`pack.mcmeta`、`tags/` 带进宿主包。

> 只交付歌曲文件夹时，`validate_pack.py --pack <歌曲文件夹>` 也能自检（不会要求 `pack.mcmeta`）。

## 3. 接歌链（播完自动下一首）

在 `song.json` 里设 `"next_song": "minecraft:music/下一首/play"`，生成的 `stop.mcfunction` 末尾会带
`function minecraft:music/下一首/play`。改单曲时**不要**动宿主的 `main`/`tick` 标签。

## 4. 多首曲子共存 / 菜单

- 每首曲子一个 `song_id`、一个 `path`，互不干扰；同一时刻只播放一首（同时播会混音）。
- 选曲就是给假玩家 `music_progress` 的 `music_type` 赋值：`/scoreboard players set music_progress music_type <id>`；
  `play.mcfunction` 做的就是这件事 + 把 `nbs_s` 归零、`nbs_t` 复位。
- 想做菜单/唱片机交互（右键切歌、暂停、歌词），参考成品包 `examples/RedstoneMusicBox-v3.zip` 的
  `data/minecraft/function/music/box/` 那一套。

## 5. 精度进阶：用 `/tick rate` 把时间网格细化 4 倍

本工作流的网格是"1 个 t = 1 个游戏 tick"。原版 20 tps 下 = **50 ms**，所以 144 BPM 的十六分音符
（104.17 ms）只能量化到 2 或 3 个 tick，最大误差 **25 ms**（半个 tick，物理下限）。

**MC 1.20.3+ 有 `/tick rate`**，把世界跑到 80 tps 后，同样 `#speed 80` 的约定下 **1 个 t = 12.5 ms**，
量化误差同样缩小 4 倍：

```bash
python3 scripts/midi_to_song.py 歌曲.mid -o song.json --tick-rate 80 --name mysong --song-id 9
# 实测（144 BPM 的 166 秒曲子）：最大量化误差 25.0 ms → 4.6 ms
```

进游戏必须**手动**敲一次 `/tick rate 80`（本工作流不会、也不该替你改全局设置）：

| 必须告知用户的事 | 说明 |
|---|---|
| 这是**全世界加速** | 红石、生物 AI、作物生长、刷怪全部一起变快 |
| **不跨会话保留** | 退出重进世界就回到 20，每次都要重敲；忘了敲 = 整曲慢 4 倍 |
| 服务器扛不住会漂 | 日志出现 `Can't keep up!` 时实际 TPS 已经掉下来了 |
| 用完记得 `/tick rate 20` | 恢复原速 |

生产建议：**默认 20 tps 出包**（谁都能放），把 80 tps 当成"用户明确要精度时"的进阶选项。

## 6. 不想用树？直接用 `/schedule` 排程（备选播放引擎）

树的优点是与 lemon 系宿主完全兼容、每刻只走一条分支。若你只要**独立数据包**且想省掉每刻开销，
可以在生成后用 `/schedule` 直接排程（**1.14+** 才有；本仓库未自动化，属手工进阶）：

```
# play_sched.mcfunction（t 为该音符的游戏 tick）
schedule function minecraft:music/mysong/notes/12 12t
schedule function minecraft:music/mysong/notes/15 15t
...
```

- 优点：不需要 `tick.json`、不需要 `#speed`、每刻零开销，时间由引擎精确调度。
- 缺点：几千条 `schedule` 一次性压进一个函数；`stop` 需要逐条 `schedule clear <函数>`；
  与需要 `#speed` 的宿主不兼容。
- 安全上限：单个 mcfunction 的命令数上限是 65536（1.20.2 起放宽），本工作流的曲目规模（千级）很安全。

## 7. 没有 Python 环境：手工拼包

按 `templates/` 里的骨架拼：`pack.mcmeta` 二选一（看版本）、`init.mcfunction`、两个标签，
再把 `generate.py` 的产物放进去。**三处必须自洽**（写法 / 目录名 / 标签路径），
详见 `templates/README.md`。手工生成 mcfunction 的规则见 `references/format_spec.md` §A、§D。

## 8. 音频不是 MIDI 时

本 skill 只吃 **MIDI / .nbs 工程 / 文字谱面**。只有 mp3 时，先自己转录成 MIDI（外部工具如
basic-pitch、piano_transcription_inference），并且**如实告诉用户质量会下降**：
纯钢琴独奏最好，人声/多乐器混音经常惨不忍睹。转录完先跑 `scan_midi.py` 看判定，
音符破碎/声部混乱就该建议用户去找原生 MIDI，而不是硬做。

## 9. 交付清单（每次都过一遍）

```
[ ] song.json（可复现的编曲输入）
[ ] 编曲决策说明（midi_to_song.py --report 自动生成：声部映射/折叠/量化误差/抽查）
[ ] 数据包目录或 zip（make_datapack.py 产出，pack.mcmeta 写法与目录名都已对版本）
[ ] validate_pack.py 全绿（含"每个 notes 恰好被引用一次"+ 树状态机模拟）
[ ] doctor.py 全 [OK]
[ ] 试听 wav（render_preview.py，可选但推荐）
[ ] 交付说明里写清：#speed 假设、是否用了 /tick rate、哪些音折了八度、验证到了哪一步
```
