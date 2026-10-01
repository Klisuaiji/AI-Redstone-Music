# 示例文件说明

| 文件 | 说明 |
|---|---|
| `demo.mid` | 8 小节示例 MIDI（120 BPM，主旋律+贝斯+鼓）。用来快速验证整条工具链，也是 `tests/smoke_test.py` 的素材：里面刻意放了一个同 tick 两音和弦和一个 1 游戏 tick 的军鼓 flam（会产生相邻音符 tick，正好踩中"2 格宽叶子静音"的坑）。由 `tests/gen_demo_midi.py` 生成 |
| `song.example.json` | song.json 最小示例（generate.py 的输入格式） |
| `datapack_demo/` | 可直接安装的独立示例数据包：《反乌托邦》前 16.5s（前奏钢琴 riff + 鼓进入 + 人声第一句），含节选 song.json 与安装说明 |
| `datapack_m3/` | **完整一曲**示例（165.8s / 2897 音符 / MC 26.2）：144 BPM 四轨 MIDI（电吉他+鼓+贝斯）全曲，含完整 song.json、26.2 的 pack.mcmeta 写法、时轴换算与编曲决策 |
| `RedstoneMusicBox-v3.zip` | 配套成品数据包：红石音乐盒 v3（12 首曲目 + 唱片机播放器 + 歌词 + 维度禁播），兼容 1.21.2–1.21.8 / 26.2 |

试试用示例 MIDI 跑一遍（零依赖）：

```bash
python3 scripts/scan_midi.py examples/demo.mid
python3 scripts/midi_to_song.py examples/demo.mid -o /tmp/demo.song.json --name demo --song-id 8
python3 scripts/render_preview.py /tmp/demo.song.json -o /tmp/demo.wav
python3 scripts/make_datapack.py /tmp/demo.song.json -o /tmp/demo-pack --mc-version 26.2
```

> `datapack_demo/` 与 `datapack_m3/` 里的 zip 是**用修复前的生成器**（2 格宽叶子）打出来的历史产物：
> 行为仍正确（`datapack_demo` 的 117 个音符都会触发），但 `datapack_demo` 有 54 个音符早响 1 个游戏 tick，
> 且 tree 的分块方式与现在重新生成的结果不同。用当前 `generate.py` 重新生成会得到 1 格宽叶子的版本
> （每个音符在游戏 tick == t 恰好触发一次）。详见 `references/format_spec.md` §A。

完整成品数据包（红石音乐盒 v2，11 首）不随 skill 仓库分发，获取方式见对应发布页。
