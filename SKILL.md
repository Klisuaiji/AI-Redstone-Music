---
name: mc-redstone-music
description: >-
  把歌曲（MIDI / .nbs 工程 / 文字谱面）转换成 Minecraft Java 版原版可播放的 mcfunction 音符盒音乐数据包，
  支持独立数据包与 lemon 兼容两种交付。当用户要求"做红石音乐""把这首歌做成我的世界音乐""MIDI 转
  mcfunction""生成音符盒音乐数据包""用指令播放这首歌""note block music datapack""MIDI to Minecraft
  music""convert a song into a Minecraft datapack""做一个能在原版 MC 里播的歌"时使用。覆盖 1.13 至
  26.x（含 pack.mcmeta 两代写法、function/functions 目录分水岭、/tick rate 精度进阶）。
---

# Minecraft 红石音乐 mcfunction 工作流

把一首歌变成**原版 Minecraft Java 版**里 `/function` 就能播的数据包（音符盒音色，不需要 mod、不需要资源包）。

## 铁律

1. 只支持 **Minecraft Java 版 ≥ 1.13**（数据包 1.13 才有）。Bedrock 没有 `/function`，直接说明并停止。
2. 所有乐器/音效 ID 必须来自 `references/instruments.md` 白名单，且满足目标版本（pling/bit/banjo 需 1.14+，
   trumpet 需 26.1+）。
3. **不知道的事不许编**：听不了音频就明说，改要 MIDI / .nbs / 文字谱面。只有 mp3 时按 `references/recipes.md` §8
   如实告知转录质量落差。
4. **时轴只有一套已验证的约定**：`time_unit=nbs_s_units` + `#speed nbs_s = 80`（此时 song.json 里的 `t`
   就是游戏 tick）。宿主 `#speed` 不是 80 时必须重标时间轴并说明，不许直接照搬。
5. **交付前必须跑自检**，且**没实机验证就不说"能听"**（见下方「交付准则」）。

## 交付准则（先读，这是最容易犯的错）

静态自检能证明的和不能证明的，必须分清：

| 证据 | 能证明什么 | 怎么拿到 |
|---|---|---|
| `validate_pack.py` 全绿 | 每个 `notes/<t>` 都被 tree 恰好引用一次、树节点全部可达、乐器/音域/pitch/CRLF/标签/song_id 全部合规，**并且用树状态机模拟证明"每个音符在游戏 tick == t 时恰好触发一次"** | 必做 |
| `render_preview.py` 出的 wav | 音高关系、节奏、声部平衡大致对（音色不是游戏音色） | 推荐 |
| 进游戏实听 | 音色、手感、有没有卡顿——**唯一最终判据** | 交付说明里如实交代 |

- **不许**在没进游戏的情况下说"已经能听了/已安装"。正确说法是：
  「静态自检全绿（含树状态机模拟）+ 试听 wav 已生成；**未在游戏内实听确认**」。
- **不许**把"数据包能加载"说成"音乐能播"。
- 做了折八度、删轨、改音量等妥协，必须写进编曲决策说明——**不要粉饰**。

## 工具一览（`scripts/`，全部零依赖，只用标准库）

| 脚本 | 什么时候用 | 一句话 |
|---|---|---|
| `scan_midi.py` | 第二步：拿到 MIDI 先体检 | 声部清单 / 音高范围 / 鼓组 GM 直方图 / 节奏网格 / 量化误差 / 一句判定 |
| `midi_to_song.py` | 第三、四步：自动编曲 | 轨道分类→乐器映射→音量表→时轴量化→八度折叠→去重，产出 song.json **+ 编曲决策报告** |
| `nbs_to_json.py` | 音源是 .nbs 工程 | OpenNBS / 经典 .nbs → song.json |
| `generate.py` | 第五步：生成 mcfunction | song.json → `play/stop/tick/notes/tree`（树窗口调度，与 lemon 参考包逐文件比对过的算法） |
| `validate_pack.py` | 第五步：硬门禁（CI 用） | tree↔notes 一致性 + 可达性 + 白名单/音域/CRLF/标签 + **树状态机模拟** |
| `make_datapack.py` | 第六步：组装交付物 | song.json → 可安装数据包 + zip；**按目标版本自动选 pack.mcmeta 两代写法与目录名** |
| `render_preview.py` | 交付前试听 | song.json → WAV（简单合成音色，不用开游戏） |
| `doctor.py` | 出问题时 | "怎么没声音"逐项体检，每条 ✗ 下面给修法 |
| `add_to_musicbox.py` | 要把歌装进红石音乐盒 | 注册/移除歌曲，自动维护曲目表、点歌菜单、歌名字幕；支持从 `.mid` 一步到位 + `.lrc` 歌词 |
| `check_refs.py` | 改完数据包 | 通用静态检查：函数引用是否都能解析、JSON 合法性、CRLF |

一条龙：

```bash
python3 scripts/scan_midi.py 歌曲.mid
python3 scripts/midi_to_song.py 歌曲.mid -o song.json --name <歌名> --song-id <编号> \
    --mc-version <版本> --report 编曲说明.md
python3 scripts/render_preview.py song.json -o preview.wav
python3 scripts/make_datapack.py song.json -o out/<歌名> --mc-version <版本>
python3 scripts/validate_pack.py --pack out/<歌名> --namespace minecraft --song <歌名> \
    --song-id <编号> --speed 80 --mc-version <版本>
```

没有 Python 环境：按 `templates/` 手工拼，规则见 `references/format_spec.md` §A/§D 与 `templates/README.md`。

## 第一步：必须向用户提问（缺一不可）

1. **MC Java 版本**（如 1.20.4 / 1.21.8 / 26.2）——决定可用乐器、目录名（`functions` vs `function`）、
   pack.mcmeta 写法、能不能用 `/tick rate`。
2. **音源形式**：MIDI / MusicXML / OpenNBS 工程 / 文字谱面？（音频请按 §8 如实说明）
3. **声部取舍**：是否保留主旋律 / 鼓组 / 和声 / 低音？可逐轨 include/exclude。
4. **交付物**：song.json / mcfunction 文件夹 / 完整可安装数据包 zip？可多选。
5. **集成方式**：A. **lemon 兼容**——用户已有音乐数据包，只交付歌曲文件夹；
   B. **独立数据包**——自带 init/tick 标签，丢进 `datapacks/` 就能用（`make_datapack.py` 负责）；
   C. **装进红石音乐盒**——用户要"唱片机 + 点歌菜单 + 歌词 + 维度禁播"那套交互时，
   用 `add_to_musicbox.py` 把歌注册进 `examples/musicbox/` 的框架（见「第六步」）。
6. lemon 兼容模式追加问：**song_id**（宿主内未占用的编号，lemon 原包占 8）、**namespace/path**、
   宿主的 **`#speed nbs_s`** 值（`/scoreboard players get #speed nbs_s`）。**不是 80 就要重标时间轴。**

## 第二步：分析音源

```bash
python3 scripts/scan_midi.py 歌曲.mid --json report.json
```

它会给出：tempo/时长、逐轨（名称·声道·音色号·音符数·音高范围·八度分布）、鼓组 GM 直方图、
节奏网格与量化误差、**声部映射判定**。把判定念给用户，并据此定编曲方案。

MIDI 实战坑（详见 `references/midi_notes.md`）：只数 note-on、别信 header format、按轨道名路由声部、
别套 16 分网格（很多转录是 1/100 拍的人性化网格）。

多源混合（MIDI 伴奏 + 音频人声）时必须先做 BPM 对齐验证（`references/midi_notes.md` §3）。

## 第三步：编曲（音源声部 → 音符盒乐器）

```bash
python3 scripts/midi_to_song.py 歌曲.mid -o song.json --name <歌名> --song-id <编号> \
    --mc-version <版本> --report 编曲说明.md
```

自动规则（可用参数覆盖）：鼓声道/鼓关键词 → basedrum 0.6 / snare 0.5 / hat 0.25；名称含 bass → `bass`；
其余轨按 `--lead-split`（默认 72）拆主旋律/和弦，`--lead-inst auto` 会优先挑"整轨塞得进单一乐器"的那个。

原则：

- 主旋律：`pling`（明亮电钢）/ `flute`（高八度补充）/ `bit`（合成）/ `harp`（中音温暖）。
  **单个乐器只有 25 个半音**，跨度大就按音区拆分或折八度（都会记进报告）。
- 低音：`bass`；和弦：`guitar` / `banjo`；高音点缀：`bell` / `chime` / `xylophone`；
  铜管仅 26.1+ 用 `trumpet` 系列。头颅乐器（1.20+）没有音高概念，**禁止用于旋律**。
- 默认混音音量（经听感校准）：人声主旋律/伴奏 1.0、bass 1.0、bit 0.5、底鼓 0.6、军鼓 0.5、踩镲 0.25。
  **鼓宁小勿大**——密集踩镲用 0.5 就会淹没全曲。
- 同 tick 同乐器的和弦**必须保留**；去重只按 `(tick, 乐器, 音高)`。
- 音域：`use-count = MIDI − 乐器基准 ∈ [0,24]`（见 `references/pitch.md`）。超界优先换八度合适的乐器，
  仍超就升降八度并**记录到交付说明**。MC 同时发声上限 255，实测峰值 4–8，很安全。

## 第四步：写出 song.json

Schema 见 `references/format_spec.md` §B，骨架见 `templates/song.template.json`。
`meta.mc_version` 填用户版本；`time_unit` 用 `nbs_s_units` + `speed`（默认 80）。

## 第五步：生成与自检

```bash
python3 scripts/generate.py song.json -o out/music/<歌名>          # lemon 兼容交付物
python3 scripts/make_datapack.py song.json -o out/<歌名> --mc-version <版本>   # 独立数据包 + zip
python3 scripts/validate_pack.py --pack out/<歌名> --namespace <ns> --song <歌名> \
    --song-id <id> --speed 80 --mc-version <版本>
```

自检清单（`validate_pack.py` 会全部覆盖）：

- **每个 `notes/<t>.mcfunction` 被 tree 恰好引用 1 次**——叶子必须 **1 格宽**；2 格宽叶子会让相邻 tick 对
  `(2k,2k+1)` 里第二个 tick 的文件没人调用（**永久静音**），还会让音符早响 1 个游戏 tick。
  细节与实测数据见 `references/format_spec.md` §A。
- 树节点全部从根可达、无悬空子节点；`tick.mcfunction` 的树根名与 tree/ 一致。
- 乐器在版本白名单内、`pitch ∈ [0.5, 2.0]`、`use-count ∈ [0,24]`。
- `play/stop/tick` 的 `song_id` 一致；末 tick 接 `stop`；所有 `.mcfunction` 为 CRLF。
- 独立模式：目录名按 `function`/`functions` 分水岭、pack.mcmeta 按版本选写法、tick/load 标签路径正确。

## 第六步：交付

- **独立数据包**：`make_datapack.py` 产出的 zip 丢进 `datapacks/` → `/reload` →
  `/function <ns>:<path>/play`；给玩家打 `no_music` 标签即静音。
- **装进红石音乐盒**：`python3 scripts/add_to_musicbox.py --box <盒子目录> --song song.json --name "歌名" [--lrc 歌词.lrc]`
  → `/reload`。盒子提供唱片机（左键上一首 / 连击长按暂停 / 右键下一首 / 双击右键菜单）、`/trigger lrc` 歌词、
  `/trigger play set <编号>` 点歌、维度禁播。详见 `examples/musicbox/README.md`。
- **lemon 兼容**：交付 `<歌名>/` 文件夹（play/stop/tick/tree/notes）+ 集成说明：放进
  `data/<ns>/function/`（1.21+）或 `functions/`（≤1.20.4）；确认宿主每刻执行本曲 `tick`、
  `#speed nbs_s = 80`、`song_id` 不冲突。**不要**带 `pack.mcmeta` / `init` / `tags` 进宿主包。
- 附上 `song.json` + 编曲决策说明（`--report` 自动生成）+ 试听 wav（可选）。
- 交付说明里写清：`#speed` 假设、是否用了 `/tick rate`、折了哪些八度、**验证到了哪一步**。

## 版本地形速查（决定"这一版能打到什么程度"）

| 版本 | 目录名 | pack.mcmeta | 乐器数 | `/tick rate` 精度进阶 |
|---|---|---|---|---|
| 1.13 | `functions/` | `pack_format` | 10 | 无（1.20.3 才有） |
| 1.14–1.20.2 | `functions/` | `pack_format` | 16 | 无 |
| 1.20.3–1.20.6 | `functions/` | `pack_format` | 16 | ✅ 可 `/tick rate 80`（网格 12.5 ms） |
| 1.21–1.21.8 | `function/`（单数!） | `pack_format` | 16 | ✅ |
| ≥1.21.9（含 26.x） | `function/` | **`min_format`/`max_format` = `[主,次]`**，不能写 `pack_format`、不能写小数 `107.1` | 16（26.1+ 多 4 种铜管） | ✅ |

完整格式数字表与两代写法：`references/datapack.md`。`make_datapack.py` 会按版本自动选对。

## 参考文件

| 文件 | 内容 |
|---|---|
| `references/format_spec.md` | 产物规范（play/stop/tick/tree/notes 逐行规则）+ song.json schema + 手工生成备忘 |
| `references/instruments.md` | 乐器白名单（版本/音域/底部方块/音效事件） |
| `references/pitch.md` | `use-count ↔ /playsound pitch` 换算表 |
| `references/datapack.md` | pack_format 全表、两代 pack.mcmeta 写法、目录分水岭、运行时事实 |
| `references/midi_notes.md` | MIDI 解析实战坑、BPM 对齐、混音音量、**交付前一致性自检** |
| `references/troubleshooting.md` | 从"没声音"到"能听"的症状→原因→修法 |
| `references/recipes.md` | 常用配方：接入 lemon 宿主、接歌链、多曲共存、**/tick rate 精度进阶**、/schedule 备选引擎 |
| `templates/` | song.json 骨架 + 独立数据包骨架（手拼时用） |
| `examples/musicbox/` | **红石音乐盒通用框架**（不含歌曲）：唱片机 + 点歌菜单 + 歌词 + 维度禁播；用 `add_to_musicbox.py` 注册歌曲 |
| `examples/demo.mid` | 8 小节示例 MIDI，用来快速验证工具链 |

## 参考产物与自检

- `examples/musicbox/`：**通用框架数据包**（不含歌曲），也可当"产物该长什么样"的对照；
  它是从同作者的成品包 v3 抽出来的，交互机制一致。
- `tests/smoke_test.py`：端到端回归测试（含"2 格宽叶子必须被抓出来"的回归用例，以及"把歌曲注册进音乐盒"的全流程）；
  `python3 tests/smoke_test.py` 应输出 `SMOKE TEST PASSED`。
- 出问题先跑 `python3 scripts/doctor.py --pack <包>`。
