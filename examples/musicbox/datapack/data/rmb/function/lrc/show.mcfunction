# Run the lyric function of the current song (every song must have an lrc.mcfunction; the tool generates it automatically)
execute store result storage rmb:io arg.id int 1 run scoreboard players get music_progress music_type
$function rmb:song/$(id)/lrc
