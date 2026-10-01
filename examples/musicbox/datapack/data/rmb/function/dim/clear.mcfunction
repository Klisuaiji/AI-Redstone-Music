# /function rmb:dim/clear —— lift the ban for every dimension
scoreboard players set #dim_o mb_cfg 0
scoreboard players set #dim_n mb_cfg 0
scoreboard players set #dim_e mb_cfg 0
tellraw @a ["",{"text":"[MusicBox] ","color":"gold"},{"text":"All dimension bans lifted","color":"green"}]
