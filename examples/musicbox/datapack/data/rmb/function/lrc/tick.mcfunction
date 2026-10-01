# 临时消息优先：mb_msg 倒计时期间不画歌词
scoreboard players remove @a[scores={mb_msg=1..}] mb_msg 1
execute as @a[tag=mb_lrc] unless score @s mb_msg matches 1.. if score music_progress music_type matches 1.. run function rmb:lrc/show
