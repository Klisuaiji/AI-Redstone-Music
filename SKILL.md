---
name: mc-redstone-music
description: 将歌曲（音频/MIDI/NBS工程/文字谱面）转换为可在原版 Minecraft Java 播放的 mcfunction 红石音乐数据包。当用户要求"做红石音乐""把歌转成 mcfunction""生成音符盒音乐数据包"时使用。
---

# Minecraft 红石音乐 mcfunction 工作流

## 铁律
1. 只支持 **Minecraft Java 版 ≥ 1.13**（数据包 1.13 才存在）。Bedrock 不支持，直接说明。
2. 所有乐器/音效 ID 必须来自 `references/instruments.md` 的白名单，且满足目标版本。
3. 不知道的事不许编：听不了音频就明说，改要 MIDI/NBS/文字谱面。

## 第一步：必须向用户提问（缺一不可）
1. **MC Java 版本**（如 1.20.4 / 1.21.4 / 26.1）——决定可用乐器、目录名（`functions` vs `function`）、pack_format。
2. **音源形式**：直接上传音频？MIDI / MusicXML / OpenNBS 工程（.nbs 或文本转储）？还是文字谱面/哼唱描述？
3. **是否包含演唱旋律轨**（主旋律，如 lemon 中 harp+guitar 承担的人声旋律）？是否保留鼓组/和声/低音轨？可逐轨 include/exclude。
4. **交付物**：① song.json ② mcfunction 文件夹 ③ 完整可安装数据包 zip。可多选。
5. **集成方式**：A.「lemon 兼容」——用户已有音乐数据包（提供 scoreboard 骨架：`music_type`/`nbs_s`/`nbs_t` 目标、`#speed` 假玩家、`no_music` 静音标签、每刻调用各曲 `tick`），只交付歌曲文件夹；B.「独立数据包」——自带 init/tick 标签。
6. 若是 lemon 兼容模式：问 **song_id**（整数，其数据包内已占用的编号，lemon=8）和 **namespace/path**（lemon 是 `minecraft:music/lemon`）；问其数据包里 `#speed nbs_s` 的值（在 init 里 `scoreboard players set #speed nbs_s N`，常见为 2）。

## 第二步：获取并分析音源
按优先级：
- **平台支持音频输入**：实际听辨，转录为「音名 + 相对节奏」。必须标注置信度，复杂和弦/鼓组可简化。人声只取旋律线。
- **MIDI / MusicXML**：直接解析音轨（track）、音符（音高/起始/时长/力度）、速度（BPM）。
  真实 MIDI 常见坑（同音高重叠、format 0 多轨、轨道名路由、粘住音符、BPM 与音频不符）见 `references/midi_notes.md`；
  **多源混合（MIDI 伴奏 + 音频人声）时必须先做 BPM 对齐验证**（midi_notes.md 第 3 节），再统一时间轴。
- **.nbs 二进制工程**：运行 `python3 scripts/nbs_to_json.py 文件.nbs -o song.json`（见 references/format_spec.md 的字段说明）。
- **文字描述**（如"F# 小调，副歌从 C#5 开始…"）：手工构建 JSON，节奏需与用户确认。

分析要点：确定调号、拍号、BPM、曲式（主歌/副歌）、各声部分工。鼓组只映射为 basedrum(底鼓)/snare(军鼓)/hat(踩镲)。

## 第三步：编曲（音源声部 → 音符盒乐器）
对照 `references/instruments.md` 选乐器，原则：
- 主旋律（含人声旋律）：`harp`（中音温暖）、`pling`（明亮电钢，1.14+）、`bit`（合成，1.14+）、`flute`（高八度补充）
- 低音：`bass`（弦贝斯）、`didgeridoo`（1.14+，低两八度）
- 和弦/分解：`guitar`（低八度）、`banjo`（1.14+）
- 鼓：`basedrum`/`snare`/`hat`（鼓声部 pitch 随意，用 use-count 12 → pitch 1.0 即可）
- 高音点缀：`bell`/`chime`/`xylophone`/`iron_xylophone`(1.14+)/`cow_bell`(1.14+)
- 铜管：仅 26.1+ 用 `trumpet` 系列
- 头颅乐器（1.20+）**没有音高概念**，禁止用于旋律，仅作特效

版本兜底：目标 1.13 时，1.14 音色全部回退（pling→harp、iron_xylophone→xylophone、bit→harp、banjo→guitar、cow_bell→bell、didgeridoo→bass）。

默认混音音量（经用户听感校准，详见 midi_notes.md 第 6 节）：人声主旋律/伴奏 harp·guitar 1.0、bass 1.0、bit 0.5、底鼓 0.6、军鼓 0.5、踩镲 0.25。**鼓宁小勿大**——密集踩镲用 0.5 就会淹没全曲（用户最常见返工原因）。同一 tick 同一乐器的多音和弦必须保留，去重只按 (tick, 乐器, pitch)。

音域：每个音符按乐器基准换算 use-count ∈ [0,24]（见 pitch.md）。超出时优先换八度合适的乐器，仍超则升/降八度并记录到交付说明。注意 MC 同时发声上限 255，密集和弦要控制同 tick 音符数（lemon 峰值约 4，很安全）。

## 第四步：写出 song.json
严格按 `references/format_spec.md` 的 schema。`meta.mc_version` 填用户版本；`time_unit` 默认 `nbs_ticks` + `tempo_tps`（BPM÷60×4 分音符？不——NBS 的 tps = 每秒钟的 NBS tick 数，4/4 拍 120BPM 常见为 10 tps）。

## 第五步：生成与校验
有代码执行环境时：
```bash
python3 scripts/generate.py song.json -o out/music/<歌名>
# lemon 兼容模式且用户提供 #speed 值时：
python3 scripts/generate.py song.json -o out/ --speed 2
```

脚本会自动：校验乐器白名单与版本、音域夹取并告警、时间量化校验（非整数报错）、生成 play/stop/tick/tree/notes（CRLF、末 tick 接 stop、单音符叶子树——与 lemon 参考包逐文件比对过的算法）。
无代码环境：按 `references/format_spec.md` 附录的手工生成规则写文件（工作量大，务必逐条核对窗口公式）。

自检清单：
- tree/ 根名与 tick.mcfunction 调用一致；notes/ 时间集合与 tree 叶子一致
- 每个 notes 文件非空、乐器在版本白名单、pitch 在 [0.5, 2.0]
- play/stop/tick 的 song_id 正确；last tick 有 `function .../stop`
- 独立模式：目录名、pack_format 按 datapack.md 对应版本；tick/load 标签路径正确

## 第六步：交付
- lemon 兼容：打包 `<path>/` 文件夹（play/stop/tick/tree/notes）为 zip，附集成说明：「放入 `data/<namespace>/function/`（1.21+）或 `data/<namespace>/functions/`（≤1.20.4），确认主数据包每刻执行本曲 tick、init 含 scoreboard 目标」。
- 独立模式：交付完整数据包（含 pack.mcmeta、init、tags），安装：丢进 `datapacks/` → `/reload` → `/function <ns>:music/<歌名>/play`。
- 附上 song.json 与「编曲决策说明」（转调、删减、乐器回退、#speed 假设）。
- **宿主包 `#speed nbs_s` 必须 = 80 时 note tick 才等于游戏 tick**（树窗口 80×t 与之配套）；换宿主先问 #speed（见 midi_notes.md 第 7 节）。

## 参考产物
`examples/RedstoneMusicBox-v2.zip`：完整可安装示例数据包「红石音乐盒 v2」（11 首歌 + 音乐盒播放器/歌词/维度禁播子系统，
兼容 1.21.2-1.21.8 / 26.2）。生成的产物格式（notes/tree/play/stop/tick、`#speed nbs_s 80`）拿它对照即可，不必逐文件猜；
其 `music/box/` 子系统是「在宿主包上做播放器 UI」的现成参考。

