# 示例数据包:m3(144 BPM MIDI 全曲,MC 26.2)

**完整一曲**的实战范例(不是节选):165.8 秒 / 2897 个音符 / 1169 个音符 tick / 树根 `0_4095`。
源文件是一份 144 BPM、4 个 MTrk 的 MIDI(`distorted electric guitar` / `drums` / `electric bass`),
用来对照"全曲规模"的产物长什么样,以及 ≥1.21.9 的 `pack.mcmeta` 该怎么写。

## 文件

| 文件 | 说明 |
|---|---|
| `m3_datapack.zip` | 可直接安装的独立数据包(5065 个文件,1.5 MB,MC 26.2 / 数据包格式 107.1) |
| `m3.song.json` | 完整的 song.json(4 个声部、2897 个音符,`time_unit: nbs_s_units`、`speed: 80`) |

zip 内容:`pack.mcmeta`、`README.txt`、`init/play/stop/tick.mcfunction`、
`notes/`(1169 个 tick,2897 行 playsound)、`tree/`(3888 个节点,树根 `0_4095`)。

## 安装与播放

```
放进存档 datapacks/ → /reload
/function minecraft:music/m3/play
/function minecraft:music/m3/stop
给自己打 no_music 标签 = 本曲静音
```

数据包含 `#speed nbs_s 80`(init.mcfunction),即 **note tick = 游戏 tick** 的时轴约定
(与 lemon 系 / LobbyMusicPack / 红石音乐盒 v3 一致,树窗口 80×t 与之配套)。

## 本例演示的两件事

### 1. 26.2 的 pack.mcmeta 写法

```json
{ "pack": { "min_format": [107, 1], "max_format": [107, 1], "description": "..." } }
```

数据包格式 82(1.21.9)是分水岭:≥82 必须用 `min_format`/`max_format` 两个 `[主,次]` 整数数组,
不能再写 `pack_format`/`supported_formats`,也不能写小数 `107.1`。详见 `references/datapack.md`。

### 2. MIDI → 游戏 tick 的时轴换算

144 BPM、480 ticks/四分音符时,1 个 MIDI tick = 1/1152 s,1 个游戏 tick = 0.05 s = 57.6 MIDI tick:

```
t(游戏 tick) = round(MIDI tick × 5 / 288)
```

十六分音符 = 2.083 游戏 tick,除不尽,所以必然有量化误差:本曲中位 **16.3 ms**、p90 24.8 ms、
最大 **25.0 ms**(正好是半个游戏 tick,20 tps 下的物理下限)。

## 编曲(声部 → 乐器 → 音量)

| MIDI 轨 | 判据 | 乐器 | 音量 | 音符数 |
|---|---|---|---|---|
| distorted electric guitar | MIDI ≥ 72(主旋律 72–92) | `flute` | 1.0 | 697 |
| distorted electric guitar | MIDI ≤ 70(强力和弦) | `guitar` | 1.0 | 700 |
| electric bass | 全部 | `bass` | 1.0 | 713 |
| drums | GM 36 / 38·40 / 其余 | `basedrum` 0.6 / `snare` 0.5 / `hat` 0.25 | — | 369 / 114 / 304 |

- 主旋律跨 21 个半音,单一音符盒乐器只有 `flute`(66–90)能覆盖;`pling`/`bit` 上限 78,
  会把 80 以上的 455 个音全部折八度,所以这里选 flute。
- 贝斯最低到 MIDI 27,低于音符盒音域下限 F#1 = MIDI 30,只能升八度(118 个音);这是硬限制。
- 同 tick 的多音和弦全部保留(去重键 = tick + 乐器 + 音高),最密同刻 8 个 playsound(上限 255)。

## 自检

```bash
unzip m3_datapack.zip -d /tmp/m3                       # 自检脚本读目录,先解压
python3 scripts/validate_pack.py --pack /tmp/m3 --namespace minecraft \
    --song m3 --song-id 9 --speed 80 --mc-version 26.2
```

输出(树状态机模拟会断言每个音符 tick 在游戏 tick == t 时恰好触发一次):

```
notes: 1169   tree 节点: 3888   可达: 3888   playsound 行: 2897
tick 范围: 2..3315  时长 165.8s   #speed=80
每个乐器的音量: {'basedrum': [0.6], 'bass': [1.0], 'flute': [1.0], 'guitar': [1.0], 'hat': [0.25], 'snare': [0.5]}
每个乐器的 use-count 区间: {'basedrum': (0, 0), 'bass': (0, 16), 'flute': (6, 21), 'guitar': (0, 24), 'hat': (0, 0), 'snare': (0, 0)}
树状态机模拟: 每个 tick 恰好触发一次

ALL CHECKS PASSED
```

> 本曲是用**修复后的** `generate.py`(1 格宽叶子)生成的。用修复前的版本生成,1169 个 notes 里会有
> **79 个不可达(静音)**、另有一批音符早响 1 tick;详见 `references/format_spec.md` §A 与
> `references/midi_notes.md` 第 9 节。
