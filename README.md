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
| 最新验证版本 | 1.21.2–1.21.8、**26.2**(pack_format 57–107.1) |
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
```

## 工作流(六步)

1. **提问**:版本 / 音源 / 声部取舍 / 交付物 / 集成方式 / song_id 与 #speed
2. **分析音源**:听辨或解析 MIDI/NBS;多源混合(MIDI 伴奏+音频人声)先做 BPM 对齐验证
3. **编曲**:声部→音符盒乐器映射 + 默认混音音量(人声/伴奏 1.0,底鼓 0.6,军鼓 0.5,踩镲 0.25)
4. **写出 song.json**(schema 见 `references/format_spec.md`)
5. **生成与自检**:generate.py 或手工规则;树根/notes 一致性、乐器白名单、音域、song_id
6. **交付**:zip + song.json + 编曲决策说明

详见 [SKILL.md](SKILL.md)。

## 示例数据包:红石音乐盒 v2

[`examples/RedstoneMusicBox-v2.zip`](examples/RedstoneMusicBox-v2.zip) 是一个**可直接安装的完整数据包**
(42,543 个文件),既是示例也是可玩的成品:

- **兼容 1.21.2–1.21.8 / 26.2**(pack_format 57–107.1)
- 11 首曲目:kagec3、sanyaose、touhoukami、lemon、After the Rain(雨停时分,含 43 句歌词)、
  baka、badapple、lunatic、popcorn、UN、shanghaitea
- 红石音乐盒播放器:附魔唱片机物品,左键上一首/长按暂停、右键下一首/双击点歌菜单,
  丢弃自动补发;`/trigger menu` 领取,`/trigger lyc` 歌词开关,`/trigger song set 0-10` 点歌
- 维度禁播(`/function minecraft:music/box/dim_ban` 等)与暂停/切歌原生联动播放链

安装:zip 放入存档 `datapacks/` → `/reload` → 按提示 `/trigger menu` 领取唱片机。
详细说明见 [`examples/README.md`](examples/README.md)。

## 仓库结构

```
SKILL.md                     # AI 技能入口:六步工作流、铁律、编曲原则
README.md                    # 本文件
references/
  format_spec.md             # lemon 数据包逆向规范 + song.json schema + 手工生成备忘
  instruments.md             # 乐器白名单(版本/音域)
  pitch.md                   # use-count ↔ /playsound pitch 换算表
  datapack.md                # pack_format 对照表、目录命名分水岭、运行时事实
  midi_notes.md              # MIDI 实战解析与对齐经验(真实交付沉淀)
scripts/
  generate.py                # song.json → mcfunction(树/notes/play/stop/tick)
  nbs_to_json.py             # .nbs → song.json
examples/
  song.example.json          # song.json 最小示例
  RedstoneMusicBox-v2.zip    # 完整示例数据包(1.21.2-1.21.8 / 26.2)
  README.md                  # 示例数据包说明
```

## 时轴约定(重要)

lemon 系宿主每刻执行 `nbs_s += #speed`,树窗口为 `80×tick`。
**note tick = 游戏 tick 要求宿主 `#speed nbs_s = 80`**(红石音乐盒 v2 与 LobbyMusicPack 均为此值)。
集成到其他数据包前先确认其 `#speed`,否则需要重标时间轴。

## 说明

- 本仓库为学习交流用途;所含曲目为对应红石音乐社区转换作品,版权归原曲作者
- 生成的音乐为音符盒合成音色,不能也不会复刻原曲音色
