# 每刻检查：只要有一个非旁观玩家处在被禁播的维度，就全局停住音乐
scoreboard players set #dim_any mb_cfg 0
execute unless score #ban mb_cfg matches 1 run return 0
execute as @a[gamemode=!spectator] at @s if dimension minecraft:overworld if score #dim_o mb_cfg matches 1 run scoreboard players set #dim_any mb_cfg 1
execute as @a[gamemode=!spectator] at @s if dimension minecraft:the_nether if score #dim_n mb_cfg matches 1 run scoreboard players set #dim_any mb_cfg 1
execute as @a[gamemode=!spectator] at @s if dimension minecraft:the_end if score #dim_e mb_cfg matches 1 run scoreboard players set #dim_any mb_cfg 1
