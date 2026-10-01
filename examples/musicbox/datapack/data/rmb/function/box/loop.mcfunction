# ---- 交互实体：一人一个；手持音乐盒时贴眼，否则头顶 2 格（不挡正常挖方块/攻击）----
execute as @a at @s anchored eyes unless entity @e[type=interaction,tag=mb_box,distance=..3] run summon interaction ~ ~ ~ {Tags:["mb_box"],width:0.5f,height:1f,response:1b}

tag @a remove mb_hold
execute as @a if items entity @s weapon.mainhand minecraft:jukebox[custom_data~{musicbox:1b}] run tag @s add mb_hold
execute as @a if items entity @s weapon.offhand minecraft:jukebox[custom_data~{musicbox:1b}] run tag @s add mb_hold

execute as @a[tag=mb_hold] at @s anchored eyes run execute as @e[type=interaction,tag=mb_box,distance=..5] at @s run tp @s ~ ~ ~
execute as @a[tag=!mb_hold] at @s anchored eyes run execute as @e[type=interaction,tag=mb_box,distance=..5] at @s run tp @s ~ ~2 ~
execute as @e[type=interaction,tag=mb_box] at @s unless entity @a[distance=..5] run kill @s

# ---- 不可丢弃：掉在地上的音乐盒直接回收，随后由下面的补发逻辑重新给一个 ----
execute as @a at @s as @e[type=item,distance=..5] if items entity @s item minecraft:jukebox[custom_data~{musicbox:1b}] run kill @s

# ---- 丢失自动补发（死亡、被 clear 等；mb_nogive = 玩家主动收回，不补）----
execute as @a[tag=!mb_nogive] unless items entity @s inventory.* minecraft:jukebox[custom_data~{musicbox:1b}] run function rmb:box/give

# ---- 采集点击：interaction 实体的 attack(左键) / interaction(右键) 字段 ----
execute as @e[type=interaction,tag=mb_box] if data entity @s attack run execute on attacker run scoreboard players set @s mb_pls 1
execute as @e[type=interaction,tag=mb_box] if data entity @s attack run data remove entity @s attack
execute as @e[type=interaction,tag=mb_box] if data entity @s interaction run execute on target run scoreboard players add @s mb_rct 1
execute as @e[type=interaction,tag=mb_box] if data entity @s interaction run data remove entity @s interaction
