# 更新记录

## 未发布（红石音乐盒）

### 新增：红石音乐盒通用框架数据包
- `examples/musicbox/`：**不含任何歌曲**的通用播放器盒子（40 个文件 / 17 KB）+ 可安装 zip。
  - `/trigger menu` 获取 / 收回**附魔唱片机**；不可放置（advancement 捕获后清掉方块）、
    不可丢弃（掉地上的立即回收）、丢失自动补发
  - 左键单击 = 上一首；连击 / 长按左键 = 暂停 · 播放；右键单击 = 下一首；双击右键 = 点歌菜单
  - 菜单是聊天栏可点击的歌名列表；`/trigger play set <编号>` 或 `/function rmb:play {song:"歌名"}`
  - `/trigger lrc` 开关歌词（动作栏，随时间轴逐句切换，支持标准 `.lrc` 导入）
  - 维度禁播：`rmb:dim/ban|unban|status|clear|on|off`；`rmb:uninstall` 一键卸载
  - `/reload` 后提示「已成功加载音乐数据包」
  - 记分板全部缩写：`menu`/`lrc`/`play` + `mb_*`；`music_type`/`nbs_s`/`nbs_t` 保持原名以兼容生成的歌曲
  - 按编号派发用**函数宏**实现，所以加歌**不需要**改任何注册代码
- `scripts/add_to_musicbox.py`：把 song.json（或直接 `.mid`）注册进盒子，自动维护曲目数量、歌名字幕、
  歌名→编号表、可点击菜单；支持 `--lrc` 歌词、`--list`、`--remove`、编号冲突保护
- `scripts/check_refs.py`：通用静态检查（函数引用能否解析 / JSON 合法性 / CRLF），改完数据包跑一下
- `tests/smoke_test.py`：新增"把 demo.mid 注册进音乐盒并校验"的全流程用例

### 移除
- `examples/datapack_demo/`（反乌托邦前 16.5s）与 `examples/datapack_m3/`（完整一曲）已删除：
  仓库示例改为**不含歌曲的通用框架**。它们是修复前生成器的产物，行为仍正确但前者有 54 个音符早响 1 tick；
  需要格式对照时按 `examples/README.md` 的命令现场生成即可。

## 上一版（工具链）

### 修复
- **`generate.py` 树叶子 bug（静音 + 早响）**：叶子条件原为 `b-a<=1`（2 格宽）却只输出 `rng[0]`。
  二分出的最深层叶子恒为对齐的 `[2k,2k+1]`，于是
  1. 相邻 tick 对 `(2k,2k+1)` 同时有音符时，`2k+1` 的 `notes/<t>.mcfunction` 会生成却**没有任何节点调用**
     → 该音符永久静音（实测某曲 1169 个 notes 里 79 个不可达；上游成品包 `after_the_rain` 491 个、
     `fanwutuobang` 85 个）；
  2. 窗口从叶子左边界起算，落在右半边的音符**早响 1 个游戏 tick（50 ms）**
     （实测上游示例包 `fanwutuobang_demo` 的 117 个 notes 里有 54 个早响）。
  改为 `y == x`（1 格宽）：窗口/守卫公式不变，时轴语义不变，树深 +1（该曲 2719 → 3888 节点）。
- `validate_pack.py`：指向歌曲文件夹时不再错误地要求 `pack.mcmeta`。

### 新增脚本
- `scan_midi.py`：MIDI 体检（声部/音域/鼓组 GM/节奏网格/量化误差）+ 一句判定。
- `midi_to_song.py`：MIDI → song.json 自动编曲（轨道分类、乐器映射、音量表、时轴量化、八度折叠、去重），
  并生成**编曲决策报告**（markdown）。
- `make_datapack.py`：song.json → 可安装数据包 + zip；按目标版本自动选两代 `pack.mcmeta` 写法与目录名，
  杜绝"26.2 写成 `pack_format` + 小数 `107.1`"这类错误。
- `render_preview.py`：song.json → WAV 试听（不用开游戏）。
- `doctor.py`：没声音排查向导（逐项 ✓/✗ + 修法 + 症状速查表）。
- `midilib.py`：共用 MIDI 读取库（只数 note-on、按轨道名路由、容错非法结构）。

### 新增能力
- **`--tick-rate`：精度进阶**。宿主跑 `/tick rate 80` 时，同样 `#speed 80` 约定下 1 个 t = 12.5 ms，
  量化误差缩小 4 倍（实测 144 BPM 曲目：最大误差 25.0 ms → 4.6 ms）。
- `midi_to_song.py` 的 `--lead-inst auto`：整轨音域塞得进单一乐器就不拆声部。
- 时间分辨率护栏：`#speed`/`tick_rate` 组合导致网格粗于 100 ms 时直接拒绝（除非 `--force`）。

### 新增测试与模板
- `tests/smoke_test.py`：端到端回归测试，含"把 tree 改回 2 格宽叶子必须被判定为 FAIL"的回归用例。
- `tests/gen_demo_midi.py` + `examples/demo.mid`：8 小节示例 MIDI（含同 tick 和弦与 1 游戏 tick 的 flam）。
- `templates/`：song.json 骨架 + 独立数据包骨架（两代 `pack.mcmeta`、init、标签）。

### 文档
- `references/troubleshooting.md`：从"没声音"到"能听"的症状 → 原因 → 修法。
- `references/recipes.md`：常用配方（接入 lemon 宿主、接歌链、多曲共存、`/tick rate` 精度进阶、
  `/schedule` 备选播放引擎、无 Python 环境手拼）。
- `SKILL.md`：新增「交付准则（证据）」与「工具一览」「版本地形速查」；frontmatter 触发词补全中英双语。
- `references/datapack.md`：新增「pack.mcmeta 的两代写法」；修正独立模式骨架里的 `pack.mcmeta` 行。
- `references/format_spec.md`：§A 写明叶子必须 1 格宽，记录两个副作用与实测数据。
- `references/midi_notes.md`：新增第 9 节「交付前必须做的一致性自检」。
- `README.md`：新增 30 秒入门、工具链表、交付准则、相关项目对比、`/tick rate` 说明。

## 更早

- 初始版本：`SKILL.md` + `references/`（格式规范、乐器白名单、音高表、数据包要点、MIDI 实战经验）+
  `scripts/generate.py`、`nbs_to_json.py` + `examples/`（示例包与成品包）。
