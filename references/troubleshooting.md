# 故障排查：从"没声音"到"能听"

先跑体检，它会逐项告诉你哪里不对并给修法：

```bash
python3 scripts/doctor.py --pack <数据包目录或zip> --mc-version <版本> \
    --namespace minecraft --song <歌名> --song-id <编号> --speed 80
```

`doctor.py` 是给人看的排查向导；`validate_pack.py` 是给 CI 的硬门禁（交付前必须过）。
下面按症状列原因——**顺序就是排查顺序**，前一步不过就别看后一步。

---

## 1. `/datapack list` 里根本没有它

| 原因 | 表现 | 修法 |
|---|---|---|
| `pack.mcmeta` 不在根目录 | 整个包被忽略 | 解压 zip 看是不是多套了一层文件夹；数据包根目录必须直接放 `pack.mcmeta` |
| `pack.mcmeta` JSON 不合法 | 列表显示"损坏或不兼容" | 常见坑：多余逗号、中文引号、BOM。用 `python3 -m json.tool pack.mcmeta` 验 |
| 版本写法错 | 26.2 上显示"不兼容" | ≥1.21.9（格式 ≥82）必须用 `min_format`/`max_format` 的 `[主,次]` 数组，**不能**写 `pack_format`，**不能**写小数 `107.1`。用 `make_datapack.py` 生成可避免 |
| 版本号超范围 | 高版本拒载低版本包 | 低版本游戏的 `max_format` 更低；跨版本要按 `references/datapack.md` 的表对齐 |

## 2. 列表里有它，但 `/function` 补全里找不到 `命名空间:路径`

| 原因 | 修法 |
|---|---|
| **目录名少/多一个 s**：1.21 起是 `data/<ns>/function/`，1.14–1.20.6 是 `data/<ns>/functions/` | 改目录名。这个错**整包静默不加载函数**，是最高频的坑 |
| 改完没 `/reload` | 任何文件改动都要 `/reload` |
| 路径拼错 | 补全里出现的才是真路径；`song.json` 的 `path` 决定 `<ns>:<path>/play` |

## 3. 有补全，`/function .../play` 之后没声音

按这个顺序查（前两条占九成）：

1. **`tick.json` 没指向本曲** —— 独立模式下 `data/minecraft/tags/function/tick.json` 的 `values` 必须包含
   `<ns>:<path>/tick`（≤1.20.4 是 `tags/functions/`）。列表里加载了不等于每刻在跑。
2. **`#speed nbs_s` 没设或是 0** —— 在 `init.mcfunction` 里。等价于每刻 `nbs_s += 0`，
   所有音符都挤在第 0 刻。
3. **`song_id` 对不上** —— `play.mcfunction` 设的 `music_type` 必须等于 `tick.mcfunction` 里
   `if score ... music_type matches N` 的 N。
4. **玩家带 `no_music` 标签** —— `playsound` 选择器是 `@a[tag=!no_music]`。
5. **在错误的世界/维度** —— 函数是每存档独立的，换存档要重新装。

> 只想确认"到底有没有在跑"：用 `--tick-rate` 之外的最简办法——`/scoreboard players get music_progress nbs_s`，
> 播放中这个值应该在增长。

## 4. 响了，但速度不对

| 症状 | 原因 |
|---|---|
| 慢/快**整数倍** | 宿主 `#speed nbs_s` 与制作时不一致。本约定要求 `#speed 80`；用 `--tick-rate 80` 制作的还必须进游戏敲 `/tick rate 80` |
| 比预期慢 4 倍 | 用 `--tick-rate 80` 做的时间轴，但世界还在 20 tps。`/tick rate 80` **退出重进会重置**，每次会话都要敲 |
| 久了会漂 | 服务器过载（日志出现 `Can't keep up!`）。减负载或换更轻的曲子 |
| 整曲快了/慢了 2 倍 | 误以为 `t=` 是秒。`t` 是游戏 tick（1/20 秒） |

## 5. 个别音符不对

| 症状 | 原因 | 修法 |
|---|---|---|
| **某几个音完全不响** | tree 叶子写成了 2 格宽（`b-a<=1`），相邻 tick 对 `(2k,2k+1)` 里第二个 tick 的 `notes/<t>` 无人调用 | 用仓库里的 `generate.py`（叶子 1 格宽）；跑 `validate_pack.py` 会直接点名 |
| 音高听着不对 | 超音域被**夹取**到边界，而不是折八度 | 生成时看 `generate.py` 的 `WARN` 行。`midi_to_song.py` 默认会自动折八度 |
| 和弦少了音 | 去重键错（按 tick+乐器 去重会吞和弦） | 去重键必须是 `(tick, 乐器, 音高)` |
| 密集段落糊 | 20 tps 网格太粗（半个 tick = 25 ms 是物理下限） | 见 `recipes.md` §5：`/tick rate 80` 把网格细化到 12.5 ms |

## 6. 声音糊 / 爆 / 太吵

- **鼓宁小勿大**：踩镲每 16 分音符一个，0.5 就会盖住全曲。默认表：底鼓 0.6 / 军鼓 0.5 / 踩镲 0.25。
- 同刻 `playsound` 过多：MC 同时发声上限 255。本工作流实测峰值通常在 4–8，很安全；如果某刻超过 30，
  考虑精简和弦。
- 多个同 tick 同乐器的音是叠加关系（不是替换），和弦越多越响。

## 7. 其他

| 现象 | 说明 |
|---|---|
| `/reload` 刷"目标已存在" | 正常。`init.mcfunction` 每次都 `objectives add`，不影响播放 |
| 播放中 `/reload` 后错乱 | 状态残留，重新 `/function .../play` 一次 |
| 多人时别人听不到 | 本工作流用 `minVolume=1` + 相对坐标，理论上全图满音量；若宿主改过 `playsound` 参数，检查 `stop`/`play` 是否被别的包覆盖 |
| 想临时禁掉一首 | `/scoreboard players set music_progress music_type -1`（清掉选曲）；或给玩家 `no_music` |

## 8. 本 skill 的能力边界（别承诺做不到的事）

- **只支持 Java 版 ≥1.13**。Bedrock 没有数据包/`/function`，直接说明。
- **音色就是音符盒音色**（harp/pling/guitar/bass/鼓 等 16 种），不会、也不该复刻原曲音色。
  想要"原曲音色"需要采样资源包 + 模组，那是另一条技术路线（见 README「相关项目」）。
- **音域硬限制**：音符盒整体 F#1–F#7（MIDI 30–102），单个乐器只有 25 个半音。低音贝斯低于 MIDI 30
  只能升八度；主旋律跨 25 个半音以上必须拆声部或折八度。这些都会被记录在编曲决策报告里。
- **`/tick rate` 是 1.20.3+ 才有**，且是全世界加速；低版本没有原版方案。
- **没有实机验证就不说"能听"**：静态自检（`validate_pack.py` 含树状态机模拟）能证明"每个音符在正确的
  游戏 tick 恰好触发一次"，`render_preview.py` 能让你先听个大概，但**音色与手感必须进游戏才算数**。
  交付时应如实说明验证到了哪一步。
