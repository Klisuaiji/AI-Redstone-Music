# 暂停 / 继续
scoreboard players set #tmp mb_cfg 0
execute if score #pau mb_cfg matches 1 run scoreboard players set #tmp mb_cfg 1
execute if score #tmp mb_cfg matches 0 run scoreboard players set #pau mb_cfg 1
execute if score #tmp mb_cfg matches 1 run scoreboard players set #pau mb_cfg 0
execute if score #pau mb_cfg matches 1 run title @a actionbar "音乐已暂停（连击/长按左键继续）"
execute unless score #pau mb_cfg matches 1 run title @a actionbar "音乐继续播放"
scoreboard players set @a mb_msg 40
