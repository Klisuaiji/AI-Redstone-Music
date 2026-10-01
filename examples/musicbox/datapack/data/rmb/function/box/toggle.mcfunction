# /trigger menu —— take it back if you have one, otherwise hand one out (runs as @s)
# Note: after clear you can no longer test "does the player have the item", so the mb_tmp tag records the state first
tag @s remove mb_nogive
tag @s remove mb_tmp
execute if items entity @s inventory.* minecraft:jukebox[custom_data~{musicbox:1b}] run tag @s add mb_tmp
execute if entity @s[tag=mb_tmp] run clear @s minecraft:jukebox[custom_data~{musicbox:1b}] 1
execute if entity @s[tag=mb_tmp] run tag @s add mb_nogive
execute if entity @s[tag=mb_tmp] run title @s title "Redstone Music Box taken back"
execute if entity @s[tag=mb_tmp] run title @s actionbar "Run /trigger menu again to get another one"
execute unless entity @s[tag=mb_tmp] run function rmb:box/give
execute unless entity @s[tag=mb_tmp] run title @s title "Redstone Music Box acquired"
execute unless entity @s[tag=mb_tmp] run title @s actionbar "Left click previous | hold left pause/play | right click next | double right click menu"
execute unless entity @s[tag=mb_tmp] run scoreboard players set @s mb_msg 60
tag @s remove mb_tmp
