# ===== Left click: single = previous song; double/hold (another left click within 16 ticks) = pause/play =====
execute as @a[tag=mb_hold] if score @s mb_pls matches 1 if score @s mb_hol matches 0 run scoreboard players set @s mb_hol 1
execute as @a[tag=mb_hold] if score @s mb_pls matches 1 if score @s mb_hol matches 0 run scoreboard players set @s mb_hct 0
execute as @a[tag=mb_hold] if score @s mb_pls matches 1 if score @s mb_hol matches 0 run scoreboard players set @s mb_don 0
execute as @a[tag=mb_hold] if score @s mb_pls matches 1 if score @s mb_hol matches 1 if score @s mb_hct matches 1..16 if score @s mb_don matches 0 run scoreboard players set #act mb_cfg 3
execute as @a if score @s mb_pls matches 1 if score @s mb_hol matches 1 if score @s mb_hct matches 1..16 run scoreboard players set @s mb_don 1
execute as @a if score @s mb_pls matches 1 if score @s mb_hol matches 1 if score @s mb_hct matches 1..16 run scoreboard players set @s mb_hol 0
execute as @a if score @s mb_pls matches 1 if score @s mb_hol matches 1 if score @s mb_hct matches 1..16 run scoreboard players set @s mb_hct 0
execute as @a if score @s mb_hol matches 1 run scoreboard players add @s mb_hct 1
execute as @a[tag=mb_hold] if score @s mb_hol matches 1 if score @s mb_hct matches 17.. if score @s mb_don matches 0 run scoreboard players set #act mb_cfg 2
execute as @a if score @s mb_hol matches 1 if score @s mb_hct matches 17.. run scoreboard players set @s mb_hol 0
execute as @a if score @s mb_hol matches 1 if score @s mb_hct matches 17.. run scoreboard players set @s mb_hct 0
scoreboard players set @a mb_pls 0

# ===== Right click: single = next song; double click within 16 ticks = open/close the menu =====
execute as @a[tag=mb_hold] if score @s mb_rct matches 1 if score @s mb_udo matches 1 run scoreboard players set @s mb_udo 0
execute as @a[tag=mb_hold] if score @s mb_rct matches 1 if score @s mb_udo matches 1 run scoreboard players set @s mb_uct 0
execute as @a[tag=mb_hold] if score @s mb_rct matches 2.. if score @s mb_uct matches ..16 if score @s mb_udo matches 0 run function rmb:box/menu_toggle
execute as @a[tag=mb_hold] if score @s mb_rct matches 2.. if score @s mb_uct matches ..16 run scoreboard players set @s mb_udo 1
execute as @a if score @s mb_rct matches 2.. run scoreboard players set @s mb_rct 0
execute as @a[tag=mb_hold] if score @s mb_rct matches 1.. if score @s mb_udo matches 0 run scoreboard players add @s mb_uct 1
execute as @a[tag=mb_hold] if score @s mb_rct matches 1.. if score @s mb_uct matches 17.. if score @s mb_udo matches 0 run scoreboard players set #act mb_cfg 1
execute as @a if score @s mb_rct matches 1.. if score @s mb_uct matches 17.. run scoreboard players set @s mb_rct 0
execute as @a if score @s mb_rct matches 1.. if score @s mb_uct matches 17.. run scoreboard players set @s mb_uct 0
