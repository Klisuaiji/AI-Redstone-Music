# ===== 左键：单击 = 上一首；连击/长按(16 刻内再次左键) = 暂停/播放 =====
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

# ===== 右键：单击 = 下一首；16 刻内双击 = 打开/关闭菜单 =====
execute as @a[tag=mb_hold] if score @s mb_rct matches 1 if score @s mb_udo matches 1 run scoreboard players set @s mb_udo 0
execute as @a[tag=mb_hold] if score @s mb_rct matches 1 if score @s mb_udo matches 1 run scoreboard players set @s mb_uct 0
execute as @a[tag=mb_hold] if score @s mb_rct matches 2.. if score @s mb_uct matches ..16 if score @s mb_udo matches 0 run function rmb:box/menu_toggle
execute as @a[tag=mb_hold] if score @s mb_rct matches 2.. if score @s mb_uct matches ..16 run scoreboard players set @s mb_udo 1
execute as @a if score @s mb_rct matches 2.. run scoreboard players set @s mb_rct 0
execute as @a[tag=mb_hold] if score @s mb_rct matches 1.. if score @s mb_udo matches 0 run scoreboard players add @s mb_uct 1
execute as @a[tag=mb_hold] if score @s mb_rct matches 1.. if score @s mb_uct matches 17.. if score @s mb_udo matches 0 run scoreboard players set #act mb_cfg 1
execute as @a if score @s mb_rct matches 1.. if score @s mb_uct matches 17.. run scoreboard players set @s mb_rct 0
execute as @a if score @s mb_rct matches 1.. if score @s mb_uct matches 17.. run scoreboard players set @s mb_uct 0
