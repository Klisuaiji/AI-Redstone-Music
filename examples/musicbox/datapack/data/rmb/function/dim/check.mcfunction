# Checked every tick: if any non-spectator player is in a banned dimension, the music stops globally
scoreboard players set #dim_any mb_cfg 0
execute unless score #ban mb_cfg matches 1 run return 0
execute as @a[gamemode=!spectator] at @s if dimension minecraft:overworld if score #dim_o mb_cfg matches 1 run scoreboard players set #dim_any mb_cfg 1
execute as @a[gamemode=!spectator] at @s if dimension minecraft:the_nether if score #dim_n mb_cfg matches 1 run scoreboard players set #dim_any mb_cfg 1
execute as @a[gamemode=!spectator] at @s if dimension minecraft:the_end if score #dim_e mb_cfg matches 1 run scoreboard players set #dim_any mb_cfg 1
