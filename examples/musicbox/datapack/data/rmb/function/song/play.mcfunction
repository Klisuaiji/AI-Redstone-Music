# 播放 #cur 指定的曲目
scoreboard players set #pau mb_cfg 0
scoreboard players operation music_progress music_type = #cur mb_cfg
execute store result storage rmb:io arg.id int 1 run scoreboard players get #cur mb_cfg
$function rmb:song/$(id)/play
function rmb:song/name
