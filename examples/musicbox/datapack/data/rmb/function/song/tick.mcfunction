# 交给宏派发到 rmb:song/<编号>/tick
execute store result storage rmb:io arg.id int 1 run scoreboard players get music_progress music_type
$function rmb:song/$(id)/tick
