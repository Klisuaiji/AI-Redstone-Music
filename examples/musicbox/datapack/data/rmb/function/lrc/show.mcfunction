# 把当前歌曲的歌词函数跑一遍（每首歌都必须有 lrc.mcfunction，工具会自动生成）
execute store result storage rmb:io arg.id int 1 run scoreboard players get music_progress music_type
$function rmb:song/$(id)/lrc
