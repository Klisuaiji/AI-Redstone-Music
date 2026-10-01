# /function rmb:dim/clear —— 解除全部维度禁播
scoreboard players set #dim_o mb_cfg 0
scoreboard players set #dim_n mb_cfg 0
scoreboard players set #dim_e mb_cfg 0
tellraw @a ["",{"text":"[音乐盒] ","color":"gold"},{"text":"已解除全部维度禁播","color":"green"}]
