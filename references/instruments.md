# 音符盒乐器白名单（来源：Minecraft Wiki "Note Block"，已核实）

## Java 1.13+（数据包起点，共 10 种）
| 乐器 ID | 中文 | 音效事件 | 底部方块 | 音域基准(use-count 0=F#) |
|---|---|---|---|---|
| harp | 竖琴(钢琴) | block.note_block.harp | 任意/空气 | F#3 (MIDI 54) |
| bass | 低音吉他 | block.note_block.bass | 木质类 | F#1 (MIDI 30) |
| basedrum | 底鼓 | block.note_block.basedrum | 石质类 | — |
| snare | 军鼓 | block.note_block.snare | 沙/砂砾 | — |
| hat | 踩镲 | block.note_block.hat | 玻璃类 | — |
| bell | 铃铛(钟琴) | block.note_block.bell | 金块 | F#5 (MIDI 78) |
| flute | 长笛 | block.note_block.flute | 黏土块 | F#4 (MIDI 66) |
| chime | 风铃 | block.note_block.chime | 浮冰 | F#5 (MIDI 78) |
| guitar | 吉他 | block.note_block.guitar | 羊毛/半砖/楼梯 | F#2 (MIDI 42) |
| xylophone | 木琴 | block.note_block.xylophone | 骨块 | F#5 (MIDI 78) |

## 1.14+ 新增（19w09a，共 6 种 → 16 种）
| iron_xylophone | 铁木琴(颤音琴) | block.note_block.iron_xylophone | 铁块 | F#3 (54) |
| cow_bell | 牛铃 | block.note_block.cow_bell | 灵魂沙 | F#3 (54) |
| didgeridoo | 迪吉里杜管 | block.note_block.didgeridoo | 南瓜 | F#1 (30) |
| bit | 比特(单簧管/合成) | block.note_block.bit | 绿宝石块 | F#3 (54) |
| banjo | 班卓 | block.note_block.banjo | 干草捆 | F#3 (54) |
| pling | 电钢 | block.note_block.pling | 萤石 | F#3 (54) |

## 1.20+（1.19.3/1.19.4 实验性；⚠ 无视 pitch，只作打击/音效）
skeleton→block.note_block.imitate.skeleton；wither_skeleton→.imitate.wither_skeleton；
zombie→.imitate.zombie；creeper→.imitate.creeper；piglin→.imitate.piglin；dragon→.imitate.ender_dragon

## 26.1+（铜块音符盒）
trumpet→block.note_block.trumpet (F#3,54)；trumpet_exposed→.trumpet_exposed (54)；
trumpet_weathered→.trumpet_weathered (F#2,42)；trumpet_oxidized→.trumpet_oxidized (42)

## NBS 工程乐器索引 → MC 乐器
0 harp, 1 bass, 2 basedrum, 3 snare, 4 hat, 5 guitar, 6 flute, 7 bell, 8 chime,
9 xylophone, 10 iron_xylophone, 11 cow_bell, 12 didgeridoo, 13 bit, 14 banjo, 15 pling
（自定义乐器：取其 sound_name，若在上方白名单则映射，否则跳过并告警）
