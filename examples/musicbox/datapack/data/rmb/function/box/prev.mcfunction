# 上一首（编号循环 1..max）
execute if score #max mb_cfg matches 0 run title @a actionbar "还没有添加歌曲"
execute if score #max mb_cfg matches 1.. run scoreboard players operation #cur mb_cfg = music_progress music_type
execute if score #max mb_cfg matches 1.. run scoreboard players remove #cur mb_cfg 1
execute if score #max mb_cfg matches 1.. if score #cur mb_cfg matches ..0 run scoreboard players operation #cur mb_cfg = #max mb_cfg
execute if score #max mb_cfg matches 1.. run function rmb:song/play
