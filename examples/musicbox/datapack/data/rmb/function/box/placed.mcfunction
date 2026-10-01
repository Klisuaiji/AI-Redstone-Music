# The music box cannot be placed: after the advancement triggers, remove the block that was just placed
execute anchored eyes positioned ^ ^ ^1 if block ~ ~ ~ minecraft:jukebox run setblock ~ ~ ~ air
execute anchored eyes positioned ^ ^ ^2 if block ~ ~ ~ minecraft:jukebox run setblock ~ ~ ~ air
execute anchored eyes positioned ^ ^ ^3 if block ~ ~ ~ minecraft:jukebox run setblock ~ ~ ~ air
tellraw @s ["",{"text":"[音乐盒] ","color":"gold"},{"text":"唱片机不能放置，已自动回收；用左右键控制播放","color":"yellow"}]
