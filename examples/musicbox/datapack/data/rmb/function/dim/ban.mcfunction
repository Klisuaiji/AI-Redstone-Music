# /function rmb:dim/ban —— 禁止在「执行者所在维度」播放
execute if dimension minecraft:overworld run scoreboard players set #dim_o mb_cfg 1
execute if dimension minecraft:the_nether run scoreboard players set #dim_n mb_cfg 1
execute if dimension minecraft:the_end run scoreboard players set #dim_e mb_cfg 1
execute if dimension minecraft:overworld run tellraw @a ["",{"text":"[音乐盒] ","color":"gold"},{"text":"已禁止在 主世界 播放","color":"yellow"}]
execute if dimension minecraft:the_nether run tellraw @a ["",{"text":"[音乐盒] ","color":"gold"},{"text":"已禁止在 下界 播放","color":"yellow"}]
execute if dimension minecraft:the_end run tellraw @a ["",{"text":"[音乐盒] ","color":"gold"},{"text":"已禁止在 末地 播放","color":"yellow"}]
