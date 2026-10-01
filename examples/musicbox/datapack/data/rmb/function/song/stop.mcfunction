# 停止当前曲目
execute if score music_progress music_type matches 1.. run scoreboard players operation #cur mb_cfg = music_progress music_type
execute if score music_progress music_type matches 1.. run function rmb:song/_stop
scoreboard players set music_progress music_type 0
scoreboard players set music_progress nbs_s 0
scoreboard players reset music_progress nbs_t
