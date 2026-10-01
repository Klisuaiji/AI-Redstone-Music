# RedstoneMusic Skill（AI 红石音乐）

把一首歌变成 **Minecraft Java 版原版可播放**的 mcfunction 音符盒音乐数据包。
不需要 mod、不需要资源包——丢进 `datapacks/`、`/reload`、`/function` 就能听。

> 生成器算法对 lemon 参考包（970 个 mcfunction）逆向并逐文件比对校正；
> 全流程在真实交付案例中验证过（12 首歌、4.6 万个 mcfunction 的数据包）。
> **全部脚本零依赖**，只用 Python 标准库。

## 这是什么（30 秒）

- **它干什么**：你给它一个 **MIDI**（或 `.nbs` 工程 / 文字谱面），它产出一个**数据包**，
  在游戏里敲 `/function <命名空间>:music/<歌名>/play` 就开始播。
- **你需要什么**：Minecraft **Java 版 ≥ 1.13**（原版即可，不要 mod）+ 会敲几条指令。就这样。
- **听起来像什么**：音符盒音色（竖琴/电钢/长笛/吉他/贝斯/鼓…）。它**不会**复刻原曲音色——
  想要"原曲音色"是另一条技术路线（见下方「相关项目」）。
- **和"搭一台红石机器"的区别**：本项目走**指令数据包**路线（`playsound` 发声音符盒采样），
  不建造实体音符盒机器。占地为零、性能开销极小、任何存档都能用。

## 快速开始

把整个 `mc-redstone-music/` 目录放进你的 skills 目录，然后对 AI 说：

> 用 mc-redstone-music 把这首歌做成红石音乐

AI 会依次确认：MC 版本 → 音源形式 → 声部取舍 → 交付物 → 集成方式（lemon 兼容需提供 song_id 与宿主
`#speed`）→ 生成并自检。

自己跑命令行也可以（一条龙，全部零依赖）：

```bash
python3 scripts/scan_midi.py 歌曲.mid                                  # 1. 体检 + 判定
python3 scripts/midi_to_song.py 歌曲.mid -o song.json \                 # 2. 自动编曲 + 决策报告
    --name mysong --song-id 9 --mc-version 26.2 --report 编曲说明.md
python3 scripts/render_preview.py song.json -o preview.wav              # 3. 先听一遍（不用开游戏）
python3 scripts/make_datapack.py song.json -o out/mysong \              # 4. 组装数据包 + zip
    --mc-version 26.2
python3 scripts/validate_pack.py --pack out/mysong --namespace minecraft \   # 5. 硬门禁
    --song mysong --song-id 9 --speed 80 --mc-version 26.2
```

先拿仓库自带的示例 MIDI 试：

```bash
python3 scripts/scan_midi.py examples/demo.mid
python3 tests/smoke_test.py            # 端到端回归测试，应输出 SMOKE TEST PASSED
```

## 工具链（`scripts/`）

| 脚本 | 作用 |
|---|---|
| `scan_midi.py` | MIDI 体检：声部/音域/鼓组/节奏网格/量化误差 + **一句判定**（该保留哪些轨、映射成什么乐器） |
| `midi_to_song.py` | MIDI → song.json 自动编曲（分类→映射→音量→量化→折八度→去重）+ **编曲决策报告** |
| `nbs_to_json.py` | OpenNBS / 经典 `.nbs` → song.json |
| `generate.py` | song.json → `play/stop/tick/notes/tree`（树窗口调度播放） |
| `validate_pack.py` | 交付前硬门禁：一致性 + 可达性 + 白名单/音域 + **树状态机模拟**（证明每个音符在正确的游戏 tick 恰好触发一次） |
| `make_datapack.py` | 组装可安装数据包 + zip；**按目标版本自动选 pack.mcmeta 两代写法与目录名** |
| `render_preview.py` | song.json → WAV 试听（简单合成音色） |
| `doctor.py` | 排查向导：从"没声音"到"能听"，每条 ✗ 下面给修法 |

## 交付准则（重要）

| 证据 | 能证明什么 |
|---|---|
| `validate_pack.py` 全绿 | 结构、音域、时轴**全部合规**；每个音符在游戏 tick == t 时**恰好触发一次** |
| `render_preview.py` 的 wav | 音高关系/节奏/声部平衡大致对 |
| **进游戏实听** | 音色与手感——**唯一最终判据** |

没进游戏就不说"能听"。详见 [`SKILL.md`](SKILL.md) 的「交付准则」。

## 兼容版本

| 项目 | 范围 |
|---|---|
| 生成目标 | Minecraft Java **1.13+**（含 26.x） |
| 目录命名 | 1.21 起 `function/`（单数）；1.14–1.20.6 是 `functions/`（复数） |
| pack.mcmeta | ≤1.21.8 用 `pack_format`；**≥1.21.9 用 `min_format`/`max_format` 的 `[主,次]` 数组**（不能写小数 `107.1`） |
| 精度进阶 | **1.20.3+** 可用 `/tick rate 80` 把时间网格从 50 ms 细化到 12.5 ms（误差 25 ms → 4.6 ms，实测） |
| 不支持 | Bedrock 版（没有数据包/`/function`） |

## 工作流（六步）

1. **提问**：版本 / 音源 / 声部取舍 / 交付物 / 集成方式 / song_id 与 `#speed`
2. **分析音源**：`scan_midi.py`；多源混合先做 BPM 对齐验证
3. **编曲**：`midi_to_song.py`；声部→乐器映射 + 混音音量表（人声/伴奏 1.0，底鼓 0.6，军鼓 0.5，踩镲 0.25）
4. **写 song.json**：schema 见 `references/format_spec.md`，骨架见 `templates/song.template.json`
5. **生成与自检**：`generate.py` / `make_datapack.py` + `validate_pack.py`
6. **交付**：zip + song.json + 编曲决策说明（并写清验证到了哪一步）

详见 [`SKILL.md`](SKILL.md)。

## 红石音乐盒（通用框架数据包）

[`examples/musicbox/`](examples/musicbox/) 是一个**不含任何歌曲**的通用播放器盒子：丢进 `datapacks/`，
用 `add_to_musicbox.py` 往里注册歌曲，就得到一个完整的音乐盒。

| 需求 | 实现 |
|---|---|
| 获取 / 收回唱片机 | `/trigger menu`（附魔唱片机；**不可放置**、**不可丢弃**，丢了自动补发） |
| 上一首 / 下一首 | 左键单击 / 右键单击 |
| 暂停 · 播放 | 连击或长按左键 |
| 点歌菜单 | 双击右键 → 聊天栏里可点击的歌名列表（也可 `/trigger play set <编号>`） |
| 按歌名点歌 | `/function rmb:play {song:"歌名"}` |
| 歌词 | `/trigger lrc` 开关，显示在动作栏，随音乐逐句切换（支持标准 `.lrc` 导入） |
| 维度禁播 | `/function rmb:dim/ban`（站在要禁播的维度里执行一次），`status` / `unban` / `clear` / `on` / `off` |
| 加载提示 | `/reload` 后屏幕显示「已成功加载音乐数据包」 |
| 记分板 | 全部缩写：`menu` `lrc` `play` + `mb_*`（`music_type` / `nbs_s` / `nbs_t` 是歌曲播放约定，保持原名以兼容本 skill 生成的歌曲） |

```bash
cp -r examples/musicbox/datapack /tmp/box
python3 scripts/add_to_musicbox.py --box /tmp/box --song 歌曲.mid --name "歌名" --lrc 歌词.lrc
python3 scripts/check_refs.py /tmp/box      # 静态检查：函数引用 / JSON / 行尾
```

细节（记分板对照表、手动添加歌曲的契约、交互实现原理、已知限制）见
[`examples/musicbox/README.md`](examples/musicbox/README.md)。需要 **MC 1.21.5+**，本包按 26.2 打包。

## 相关项目（另一条技术路线）

[**Cohenjikan/McMusicMaker**](https://github.com/Cohenjikan/McMusicMaker) 做的是**实体音符盒机器**：
用 RedPiano 模组 + 采样资源包，在世界里真正搭出音符盒/红石机器（`inplace` / `swave` / `multilane` 等形态），
依赖 Fabric、`/tick rate 80` 与资源包，音色是采样钢琴（更接近原曲），但占地大、要装 mod。

|  | 本项目（数据包） | McMusicMaker（实体机器） |
|---|---|---|
| 依赖 | 无（原版） | Fabric + RedPiano 模组 + 采样资源包 |
| 声音 | 音符盒 16 音色 | 采样钢琴等（103 音色） |
| 占地 | 0 | 随曲子长度增长 |
| 播放 | `/function .../play` | 进世界搭机器后按按钮 |
| 版本 | 1.13+ | 见其 `docs/VERSION_TACTICS.md` |

两条路线不冲突：想要"零依赖、随手能播"选本项目；想要"实体机器 + 原曲音色"选 McMusicMaker。
本项目的 `/tick rate` 精度进阶思路也参考了那条路线的量化经验。

## 仓库结构

```
SKILL.md                       # AI 技能入口：铁律、交付准则、工具一览、六步工作流
README.md                      # 本文件
CHANGELOG.md                   # 更新记录
references/
  format_spec.md               # 产物规范 + song.json schema + 手工生成备忘
  instruments.md               # 乐器白名单（版本/音域）
  pitch.md                     # use-count ↔ /playsound pitch 换算表
  datapack.md                  # pack_format 全表、两代 pack.mcmeta 写法、目录分水岭、运行时事实
  midi_notes.md                # MIDI 实战解析与对齐经验 + 交付前一致性自检
  troubleshooting.md           # 症状 → 原因 → 修法
  recipes.md                   # 常用配方（含 /tick rate 精度进阶、/schedule 备选引擎）
scripts/
  scan_midi.py                 # MIDI 体检报告
  midi_to_song.py              # MIDI → song.json 自动编曲
  nbs_to_json.py               # .nbs → song.json
  generate.py                  # song.json → mcfunction（树/notes/play/stop/tick）
  validate_pack.py             # 交付前自检（含树状态机模拟）
  make_datapack.py             # 组装独立数据包 + zip（两代 pack.mcmeta）
  add_to_musicbox.py           # 把歌曲注册进红石音乐盒（曲目表 / 菜单 / 歌词）
  check_refs.py                # 通用静态检查：函数引用 / JSON / CRLF
  render_preview.py            # song.json → WAV 试听
  doctor.py                    # 没声音排查向导
  midilib.py                   # 共用 MIDI 读取库
templates/
  song.template.json           # song.json 骨架（带字段说明）
  standalone/                  # 独立数据包骨架（pack.mcmeta 两代 + init + 标签）
tests/
  smoke_test.py                # 端到端回归测试（含"2 格宽叶子静音"回归用例）
  gen_demo_midi.py             # 生成 examples/demo.mid
examples/
  musicbox/                    # 红石音乐盒：通用框架数据包 + zip + 说明（不含歌曲）
  demo.mid                     # 8 小节示例 MIDI
  song.example.json            # song.json 最小示例
  RedstoneMusicBox-v3.zip      # 配套成品：红石音乐盒 v3（12 首 + 播放器）
```

## 时轴约定（重要）

lemon 系宿主每刻执行 `nbs_s += #speed`，树窗口为 `80×tick`。
**`#speed nbs_s = 80` 时 note tick = 游戏 tick**（1 个 t = 1/20 秒）。
集成到其他数据包前先确认其 `#speed`，否则需要重标时间轴。

**精度进阶（1.20.3+）**：进游戏敲 `/tick rate 80` 后，同样的约定下 1 个 t = 12.5 ms，
量化误差缩小 4 倍。代价是全世界加速、退出重进会重置、服务器过载会漂——详见
[`references/recipes.md`](references/recipes.md) §5。

## 说明

- 本仓库为学习交流用途；所含曲目为对应红石音乐社区转换作品，版权归原曲作者
- 生成的音乐为音符盒合成音色，不能也不会复刻原曲音色
- Bedrock 版不支持
