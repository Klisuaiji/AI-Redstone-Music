# 示例数据包:fanwutuobang_demo(反乌托邦 前 16.5s)

真实交付案例的节选:**反乌托邦**(song_id 16,交付于 LobbyMusicPack_song17_v3 数据包)的前 16.5 秒,
包含三个典型声部,方便对照检查生成产物的格式:

- **前奏钢琴 riff**(0–16.4s):MIDI acoustic guitar 轨 → `harp`/`guitar`(高音≥54→harp,低音→guitar),vol 1.0
- **鼓组**(10.04s 进):MIDI drums 轨 → basedrum 0.6 / snare 0.5 / hat 0.25(GM:36→底鼓,38/40→军鼓,其余→踩镲)
- **人声旋律**(16.49s 起):音频提取的 pling 主旋律,vol 1.0(示范人声独立轨)

## 文件

| 文件 | 说明 |
|---|---|
| `fanwutuobang_demo_datapack.zip` | 可直接安装的独立数据包(1.21+,pack_format 48,`function/` 目录命名) |
| `fanwutuobang_demo.song.json` | 上面三个声部的 song.json 节选(前奏第 1 小节 + 鼓进入 + 人声前 3 个音) |
| `stage/`(打包后已删除) | 生成时的展开目录 |

zip 内容共 408 个文件:`pack.mcmeta`、`init/play/stop/tick.mcfunction`、
`notes/`(117 个 tick)、`tree/`(284 个节点,树根 `0_511`)。

## 安装与播放

```
放进存档 datapacks/ → /reload
/function minecraft:music/fanwutuobang_demo/play
```

数据包含 `#speed nbs_s 80`(init.mcfunction)——即 **note tick = 游戏 tick** 的时轴约定
(与 LobbyMusicPack / lemon 系数据包一致,树窗口 80×t 与之配套)。
如果集成到已有音乐数据包,删除 init.mcfunction 和 load.json,确认宿主的 `#speed nbs_s` 与此一致。

## 本例展示的经验(详见 references/midi_notes.md)

- 鼓组音量必须显著低于旋律(踩镲每 16 分音符一个,0.5 就会淹没全曲);
- 伴奏/人声 1.0 为基准;
- MIDI 鼓轨 10.04s 才进入是**正确的**——音频 onset 检测把前奏的钢琴低音误报成了底鼓;
- 同一 tick 的多音和弦全部保留(去重只按 tick+乐器+音高)。
