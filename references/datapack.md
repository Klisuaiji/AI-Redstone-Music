# 数据包版本要点（wiki "Data pack"）
## pack.mcmeta pack_format 对照
1.13–1.14.4=4 | 1.15–1.16.1=5 | 1.16.2–1.16.5=6 | 1.17=7 | 1.18–1.18.1=8 | 1.18.2=9 |
1.19–1.19.3=10 | 1.19.4=12 | 1.20–1.20.1=15 | 1.20.2=18 | 1.20.3–1.20.4=26 |
1.20.5–1.20.6=41 | 1.21–1.21.1=48 | 1.21.2–1.21.3=57 | 1.21.4=61 | 1.21.5=71 |
1.21.6=80 | 1.21.7–1.21.8=81 | 1.21.9–1.21.10=88.0(含 minor 版本号) | 1.21.11=94.1 | 26.1=101.1 | 26.2=107.1 | 26.3=121.0
（最低要求 pack_format ≤ 目标版本即可被加载，高版本 pack 旧游戏拒载）

## 目录名分水岭（1.21 = 24w21a 改名）
- ≤1.20.4：`data/<ns>/functions/xxx.mcfunction`，标签 `data/<ns>/tags/functions/tick.json`
- ≥1.21：  `data/<ns>/function/xxx.mcfunction`， 标签 `data/<ns>/tags/function/tick.json`

## 独立模式最小骨架
```

pack.mcmeta                        {"pack":{"pack_format":<上表>,"description":"<歌名> 红石音乐"}}
data//function/music//play.mcfunction ...（generate.py 产物）
data//function/music/init.mcfunction
scoreboard objectives add music_type dummy
scoreboard objectives add nbs_s dummy
scoreboard objectives add nbs_t dummy
scoreboard players set #speed nbs_s 2
data//tags/function/tick.json  {"values":[":music//tick"]}   # ≤1.20.4 用 tags/functions/
data//tags/function/load.json  {"values":[":music/init"]}

```
播放：/function <ns>:music/<song>/play；给玩家打 `no_music` tag 即静音。

## 集成（lemon 兼容）模式前提
用户数据包必须已存在：scoreboard 目标 music_type/nbs_s/nbs_t；假玩家 #speed（nbs_s 上）；每刻执行各曲 tick.mcfunction；播放链用 music_type=<song_id> 选曲。交付物只需歌曲目录，song_id 不得冲突。

## 运行时事实
- /playsound：<sound> <source> <targets> [pos] [volume] [pitch] [minVolume]；JE pitch ∈ [0.5,2.0]
- volume 是「可闻半径倍数」（1=16 格），不放大响度；lemon 用 minVolume=1 + 相对坐标使全图玩家满音量收听
- 同时发声上限 255（wiki "Sound"）；超密集和弦需精简
- 1.20.2+ 函数宏以 $ 开头，本工作流勿用；1.18+ 记分板名长度限制已放宽，music_progress(14字符) 全版本安全
