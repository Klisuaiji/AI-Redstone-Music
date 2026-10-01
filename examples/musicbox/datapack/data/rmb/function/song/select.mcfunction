# /trigger play set <number>
scoreboard players operation #cur mb_cfg = @s mb_song
execute if score #max mb_cfg matches 0 run title @s actionbar "No songs have been added yet (register them with scripts/add_to_musicbox.py)"
execute if score #max mb_cfg matches 1.. if score #cur mb_cfg > #max mb_cfg run tellraw @s ["",{"text":"[MusicBox] ","color":"gold"},{"text":"No such song. Valid song numbers are 1~","color":"yellow"},{"score":{"name":"#max","objective":"mb_cfg"}},{"text":"; open the menu with /trigger menu and pick one","color":"gray"}]
execute if score #max mb_cfg matches 1.. if score #cur mb_cfg matches 1.. if score #cur mb_cfg <= #max mb_cfg run function rmb:song/play
