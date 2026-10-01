# RedstoneMusic Skill(AI 红石音乐)

把歌曲转换成 **Minecraft Java 版原版可播放**的 mcfunction 红石音乐数据包的 AI 技能(Skill)。
支持从音频、MIDI、OpenNBS 工程(.nbs)或文字谱面生成音符盒音乐,兼容 lemon 系音乐数据包
与独立数据包两种交付模式。

> 生成器算法对 lemon 参考包(970 个 mcfunction)逆向并逐文件比对校正;
> 全流程在真实交付案例中验证过(12 首歌、4.6 万个 mcfunction 的数据包)。

## 功能特性

- **多音源**:音频听辨转录 / MIDI / MusicXML / .nbs 工程 / 文字谱面
- **多交付模式**:song.json → mcfunction 文件夹 / lemon 兼容(挂接到已有音乐数据包)/ 独立数据包 zip
- **版本兜底**:1.13 起全版本乐器白名单校验,1.14+ 音色自动回退(如 pling→harp)
- **音域保护**:use-count ∈ [0,24] 换算与夹取告警(pitch ∈ [0.5, 2.0],不依赖运行时钳制)
- **高性能树查找**:二叉树窗口调度播放(与 lemon 逐文件一致的算法),万级音符 tick 无每刻遍历
- **实战经验沉淀**:MIDI 解析坑、BPM 对齐验证、混音音量表、`#speed=80` 时轴约定(见 `references/midi_notes.md`)

## 兼容版本

| 项目 | 范围 |
|---|---|
| 生成目标 | Minecraft Java 1.13+(`function/` vs `functions/` 目录、pack_format 自动对应) |
| 最新验证版本 | 1.21.2–1.21.8、**26.2**(数据包格式 57–107.1;≥1.21.9 的 `pack.mcmeta` 改用 `min_format`/`max_format` 数组写法) |
| 不支持 | Bedrock 版 |

## 快速开始

把整个 `mc-redstone-music/` 目录放入你的 skills 目录,然后对 AI 说:

> 用 mc-redstone-music 把这首歌做成红石音乐

AI 会依次确认:MC 版本 → 音源形式 → 声部取舍(人声/鼓/和声逐轨 include/exclude)→
交付物 → 集成方式(lemon 兼容需提供 song_id 与宿主 `#speed nbs_s` 值)→ 生成并自检。

有 python3 环境时可直接用脚本:

```bash
python3 scripts/generate.py song.json -o out/music/<歌名>
python3 scripts/generate.py song.json -o out/ --speed 80   # lemon 兼容,宿主 #speed=80
python3 scripts/nbs_to_json.py 文件.nbs -o song.json
python3 scripts/validate_pack.py --pack out --namespace minecraft --song <歌名> --song-id 9 --speed 80  # 交付前自检
```

## 工作流(六步)

1. **提问**:版本 / 音源 / 声部取舍 / 交付物 / 集成方式 / song_id 与 #speed
2. **分析音源**:听辨或解析 MIDI/NBS;多源混合(MIDI 伴奏+音频人声)先做 BPM 对齐验证
3. **编曲**:声部→音符盒乐器映射 + 默认混音音量(人声/伴奏 1.0,底鼓 0.6,军鼓 0.5,踩镲 0.25)
4. **写出 song.json**(schema 见 `references/format_spec.md`)
5. **生成与自检**:generate.py 或手工规则;树根/notes 一致性、乐器白名单、音域、song_id
6. **交付**:zip + song.json + 编曲决策说明

详见 [SKILL.md](SKILL.md)。

## 示例数据包:fanwutuobang_demo

[`examples/datapack_demo/`](examples/datapack_demo/) 内有**可直接安装**的独立示例数据包:
真实交付曲《反乌托邦》的前 16.5 秒(117 个音符 tick / 树根 0_511),包含三个典型声部,
生成的产物格式(notes/tree/play/stop/tick)拿它对照即可,不必逐文件猜:

- **前奏钢琴 riff**(0–16.4s):MIDI acoustic guitar 轨 → `harp`/`guitar`,vol 1.0
- **鼓组**(10.04s 进):MIDI drums 轨 → basedrum 0.6 / snare 0.5 / hat 0.25(GM:36→底鼓,38/40→军鼓,其余→踩镲)
- **人声旋律**(16.49s 起):音频提取的 pling 主旋律,vol 1.0(人声独立轨)

安装:zip 放入存档 `datapacks/` → `/reload` → `/function minecraft:music/fanwutuobang_demo/play`。
详细说明见 [`examples/datapack_demo/README.md`](examples/datapack_demo/README.md)。

## 示例数据包:m3(144 BPM MIDI 全曲 + 26.2)

[`examples/datapack_m3/`](examples/datapack_m3/) 是一整首曲子的实战范例(165.8 秒 / 2897 个音符 /
1169 个音符 tick / 树根 `0_4095`),源文件是 144 BPM 的四轨 MIDI(电吉他 / 鼓 / 贝斯):

- 电吉他 MIDI ≥72(主旋律跨 72–92,21 个半音)→ `flute` vol 1.0(只有 flute 的 66–90 能一把覆盖,
  pling/bit 只到 78,会把 80 以上的音全折八度)
- 电吉他 MIDI ≤70(强力和弦)→ `guitar` vol 1.0;贝斯 → `bass` vol 1.0(最低 MIDI 27 低于音符盒下限
  F#1=30,只能升八度);鼓 → basedrum 0.6 / snare 0.5 / hat 0.25

同时演示两件事:**26.2 的 `pack.mcmeta` 写法**(`min_format`/`max_format` = `[107,1]`,不能写小数)、
以及**时轴换算**(MIDI 144 BPM 按 20 tps 量化,误差中位 16.3 ms / 最大 25 ms = 半个游戏 tick 的物理下限)。
安装:zip 放入存档 `datapacks/` → `/reload` → `/function minecraft:music/m3/play`。
详细说明见 [`examples/datapack_m3/README.md`](examples/datapack_m3/README.md)。

## 配套成品:红石音乐盒 v3

[`examples/RedstoneMusicBox-v3.zip`](examples/RedstoneMusicBox-v3.zip) 是本 skill 工作流产出的**完整成品数据包**
(46,280 个文件,兼容 1.21.2–1.21.8 / 26.2):12 首曲目(含《反乌托邦》全曲——伴奏/鼓组完全同步 MIDI、
人声 pling 主旋律、LRC 歌词 49 句)+ 音乐盒播放器(附魔唱片机物品:左键上一首/长按暂停、右键下一首/
双击菜单、丢弃自动补发、二次 `/trigger redstonemusic:menu` 收回)、歌词开关、维度禁播等子系统。
安装:zip 放入 `datapacks/` → `/reload` → `/trigger redstonemusic:menu`。

## 仓库结构

```
SKILL.md                     # AI 技能入口:六步工作流、铁律、编曲原则
README.md                    # 本文件
references/
  format_spec.md             # lemon 数据包逆向规范 + song.json schema + 手工生成备忘
  instruments.md             # 乐器白名单(版本/音域)
  pitch.md                   # use-count ↔ /playsound pitch 换算表
  datapack.md                # pack_format 对照表(至 26.3)、两代 pack.mcmeta 写法、目录命名分水岭、运行时事实
  midi_notes.md              # MIDI 实战解析与对齐经验 + 交付前一致性自检(真实交付沉淀)
scripts/
  generate.py                # song.json → mcfunction(树/notes/play/stop/tick)
  nbs_to_json.py             # .nbs → song.json
  validate_pack.py           # 交付前自检:tree↔notes 一致性 + 树状态机模拟 + 白名单/音域/CRLF/标签
examples/
  song.example.json          # song.json 最小示例
  datapack_demo/             # 独立示例数据包(反乌托邦前 16.5s)+ 节选 song.json + 说明
  datapack_m3/               # 完整一曲示例(165.8s / 2897 音符 / MC 26.2)+ 完整 song.json + 说明
  README.md                  # 示例文件说明
```

## 时轴约定(重要)

lemon 系宿主每刻执行 `nbs_s += #speed`,树窗口为 `80×tick`。
**note tick = 游戏 tick 要求宿主 `#speed nbs_s = 80`**(红石音乐盒 v2 与 LobbyMusicPack 均为此值)。
集成到其他数据包前先确认其 `#speed`,否则需要重标时间轴。

## 说明

- 本仓库为学习交流用途;所含曲目为对应红石音乐社区转换作品,版权归原曲作者
- 生成的音乐为音符盒合成音色,不能也不会复刻原曲音色
