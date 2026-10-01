# 数据包版本要点（wiki "Data pack"）
## pack.mcmeta pack_format 对照
1.13–1.14.4=4 | 1.15–1.16.1=5 | 1.16.2–1.16.5=6 | 1.17=7 | 1.18–1.18.1=8 | 1.18.2=9 |
1.19–1.19.3=10 | 1.19.4=12 | 1.20–1.20.1=15 | 1.20.2=18 | 1.20.3–1.20.4=26 |
1.20.5–1.20.6=41 | 1.21–1.21.1=48 | 1.21.2–1.21.3=57 | 1.21.4=61 | 1.21.5=71 |
1.21.6=80 | 1.21.7–1.21.8=81 | 1.21.9–1.21.10=88.0(含 minor 版本号) | 1.21.11=94.1 | 26.1=101.1 | 26.2=107.1 | 26.3=121.0
（最低要求 pack_format ≤ 目标版本即可被加载，高版本 pack 旧游戏拒载）

## pack.mcmeta 的两代写法（数据包格式 82 = 1.21.9 分水岭，重要）
- 目标 **≤1.21.8（格式 ≤81）**：写 `pack_format`（可加 `supported_formats`）
- 目标 **≥1.21.9（格式 ≥82，含 26.1/26.2/26.3）**：**必须**写 `min_format` + `max_format` 两个 `[主,次]` 整数数组，
  **不能**再出现 `pack_format` / `supported_formats`；也**不能写小数**（❌ `107.1` → ✅ `[107,1]`）
- 同时兼容 82 前后：四个字段都要给，且 `min_format[0]` 必须等于 `supported_formats` 的最小值
- 只写 `pack_format` 的旧写法在 ≥1.21.9 上会被判为不兼容（上游 RedstoneMusicBox-v3 用的就是
  `pack_format:57` + `supported_formats:{min:57,max:107.1}` 这种跨边界混合写法，且缺 min/max_format）
- 26.2 实例：`{"pack":{"min_format":[107,1],"max_format":[107,1],"description":"<歌名> 红石音乐"}}`

## 目录名分水岭（1.21 = 24w21a 改名）
- ≤1.20.4：`data/<ns>/functions/xxx.mcfunction`，标签 `data/<ns>/tags/functions/tick.json`
- ≥1.21：  `data/<ns>/function/xxx.mcfunction`， 标签 `data/<ns>/tags/function/tick.json`

## 独立模式最小骨架
```

pack.mcmeta                        {"pack":{"pack_format":<上表>,"description":"<歌名> 红石音乐"}}      # ≤1.21.8
                                   目标 ≥1.21.9 改为 {"pack":{"min_format":[主,次],"max_format":[主,次],"description":"..."}}
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
