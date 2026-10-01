# 独立模式初始化（/reload 时由 tags/function/load.json 调用）
# 注意：objective 已存在时 add 会报"已存在"，属正常现象，不影响播放
scoreboard objectives add music_type dummy
scoreboard objectives add nbs_s dummy
scoreboard objectives add nbs_t dummy
# #speed = 宿主每刻给 nbs_s 的增量。80 → song.json 里的 t 就是游戏 tick（树窗口 80×t 与之配套）
scoreboard players set #speed nbs_s 80
