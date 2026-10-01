# 示例文件说明

| 文件 | 说明 |
|---|---|
| `musicbox/` | **红石音乐盒（通用框架数据包）**：附魔唱片机 + 点歌菜单 + 歌词 + 维度禁播，**不含任何歌曲**。歌曲用 `scripts/add_to_musicbox.py` 注册进来 |
| `demo.mid` | 8 小节示例 MIDI（120 BPM，主旋律+贝斯+鼓）。用来快速验证整条工具链，也是 `tests/smoke_test.py` 的素材：里面刻意放了一个同 tick 两音和弦和一个 1 游戏 tick 的军鼓 flam（会产生相邻音符 tick，正好踩中"2 格宽叶子静音"的坑）。由 `tests/gen_demo_midi.py` 生成 |
| `song.example.json` | song.json 最小示例（generate.py 的输入格式） |
| `RedstoneMusicBox-v3.zip` | 配套**成品**数据包（历史交付物）：红石音乐盒 v3，12 首曲目 + 唱片机播放器 + 歌词 + 维度禁播，兼容 1.21.2–1.21.8 / 26.2。`musicbox/` 就是把它抽成"不含歌曲的通用框架"的结果 |

## 先试试示例 MIDI（零依赖）

```bash
python3 scripts/scan_midi.py examples/demo.mid
python3 scripts/midi_to_song.py examples/demo.mid -o /tmp/demo.song.json --name demo --song-id 1
python3 scripts/render_preview.py /tmp/demo.song.json -o /tmp/demo.wav
python3 scripts/make_datapack.py /tmp/demo.song.json -o /tmp/demo-pack --mc-version 26.2
```

## 再试试红石音乐盒

```bash
cp -r examples/musicbox/datapack /tmp/box          # 拿一份副本改
python3 scripts/add_to_musicbox.py --box /tmp/box --song examples/demo.mid --name "示例曲"
python3 scripts/check_refs.py /tmp/box             # 静态检查：函数引用 / JSON / 行尾
# 把 /tmp/box 丢进存档 datapacks/ → /reload → /trigger menu
```

> 关于仓库里不再随附的两个示例数据包：`datapack_demo`（反乌托邦前 16.5s）与 `datapack_m3`
> （完整一曲）已按需求移除，仓库示例改为**不含歌曲的通用框架**。它们是用修复前的生成器
> （2 格宽叶子）打出来的历史产物，行为仍正确但 `datapack_demo` 有 54 个音符早响 1 个游戏 tick；
> 需要"生成的产物长什么样"的对照，现在用上面的命令现场生成即可（`generate.py` 是修复后的版本）。

完整成品数据包（红石音乐盒 v2，11 首）不随 skill 仓库分发，获取方式见对应发布页。
