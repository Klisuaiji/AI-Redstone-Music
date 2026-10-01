# /function rmb:dim/unban —— 解除「执行者所在维度」的禁播
execute if dimension minecraft:overworld run scoreboard players set #dim_o mb_cfg 0
execute if dimension minecraft:the_nether run scoreboard players set #dim_n mb_cfg 0
execute if dimension minecraft:the_end run scoreboard players set #dim_e mb_cfg 0
execute if dimension minecraft:overworld run tellraw @a ["",{"text":"[音乐盒] ","color":"gold"},{"text":"已解除 主世界 禁播","color":"green"}]
execute if dimension minecraft:the_nether run tellraw @a ["",{"text":"[音乐盒] ","color":"gold"},{"text":"已解除 下界 禁播","color":"green"}]
execute if dimension minecraft:the_end run tellraw @a ["",{"text":"[音乐盒] ","color":"gold"},{"text":"已解除 末地 禁播","color":"green"}]
