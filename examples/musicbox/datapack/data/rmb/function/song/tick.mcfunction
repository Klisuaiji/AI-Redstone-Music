# Dispatch to rmb:song/<number>/tick via the macro
execute store result storage rmb:io arg.id int 1 run scoreboard players get music_progress music_type
$function rmb:song/$(id)/tick
