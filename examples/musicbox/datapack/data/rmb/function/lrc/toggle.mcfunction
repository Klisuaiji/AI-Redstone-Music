# /trigger lrc —— 开关歌词（以 @s 执行）
execute unless entity @s[tag=mb_lrc] run scoreboard players set @s mb_lyc 2
execute if entity @s[tag=mb_lrc] run scoreboard players set @s mb_lyc 3
execute if score @s mb_lyc matches 2 run tag @s add mb_lrc
execute if score @s mb_lyc matches 2 run title @s actionbar "歌词显示已开启"
execute if score @s mb_lyc matches 3 run tag @s remove mb_lrc
execute if score @s mb_lyc matches 3 run title @s actionbar "歌词显示已关闭"
scoreboard players set @s mb_msg 40
