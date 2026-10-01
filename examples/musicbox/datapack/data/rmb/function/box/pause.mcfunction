# Pause / resume
scoreboard players set #tmp mb_cfg 0
execute if score #pau mb_cfg matches 1 run scoreboard players set #tmp mb_cfg 1
execute if score #tmp mb_cfg matches 0 run scoreboard players set #pau mb_cfg 1
execute if score #tmp mb_cfg matches 1 run scoreboard players set #pau mb_cfg 0
execute if score #pau mb_cfg matches 1 run title @a actionbar "Music paused (double/hold left click to resume)"
execute unless score #pau mb_cfg matches 1 run title @a actionbar "Music resumed"
scoreboard players set @a mb_msg 40
