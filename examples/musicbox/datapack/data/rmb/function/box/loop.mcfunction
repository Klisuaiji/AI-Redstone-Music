# ---- Interaction entity: one per player; at eye level while holding the music box, otherwise 2 blocks above the head (does not get in the way of normal block breaking/attacking) ----
execute as @a at @s anchored eyes unless entity @e[type=interaction,tag=mb_box,distance=..3] run summon interaction ~ ~ ~ {Tags:["mb_box"],width:0.5f,height:1f,response:1b}

tag @a remove mb_hold
execute as @a if items entity @s weapon.mainhand minecraft:jukebox[custom_data~{musicbox:1b}] run tag @s add mb_hold
execute as @a if items entity @s weapon.offhand minecraft:jukebox[custom_data~{musicbox:1b}] run tag @s add mb_hold

execute as @a[tag=mb_hold] at @s anchored eyes run execute as @e[type=interaction,tag=mb_box,distance=..5] at @s run tp @s ~ ~ ~
execute as @a[tag=!mb_hold] at @s anchored eyes run execute as @e[type=interaction,tag=mb_box,distance=..5] at @s run tp @s ~ ~2 ~
execute as @e[type=interaction,tag=mb_box] at @s unless entity @a[distance=..5] run kill @s

# ---- Cannot be dropped: a music box on the ground is collected immediately, then the re-issue logic below hands out a new one ----
execute as @a at @s as @e[type=item,distance=..5] if items entity @s item minecraft:jukebox[custom_data~{musicbox:1b}] run kill @s

# ---- Auto re-issue when lost (death, cleared, etc.; mb_nogive = the player took it back on purpose, so do not re-issue) ----
execute as @a[tag=!mb_nogive] unless items entity @s inventory.* minecraft:jukebox[custom_data~{musicbox:1b}] run function rmb:box/give

# ---- Click capture: the attack (left click) / interaction (right click) fields of the interaction entity ----
execute as @e[type=interaction,tag=mb_box] if data entity @s attack run execute on attacker run scoreboard players set @s mb_pls 1
execute as @e[type=interaction,tag=mb_box] if data entity @s attack run data remove entity @s attack
execute as @e[type=interaction,tag=mb_box] if data entity @s interaction run execute on target run scoreboard players add @s mb_rct 1
execute as @e[type=interaction,tag=mb_box] if data entity @s interaction run data remove entity @s interaction
