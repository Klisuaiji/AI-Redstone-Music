# The music box cannot be placed: after the advancement triggers, remove the block that was just placed
execute anchored eyes positioned ^ ^ ^1 if block ~ ~ ~ minecraft:jukebox run setblock ~ ~ ~ air
execute anchored eyes positioned ^ ^ ^2 if block ~ ~ ~ minecraft:jukebox run setblock ~ ~ ~ air
execute anchored eyes positioned ^ ^ ^3 if block ~ ~ ~ minecraft:jukebox run setblock ~ ~ ~ air
tellraw @s ["",{"text":"[MusicBox] ","color":"gold"},{"text":"The music box cannot be placed; it was collected automatically. Use the left/right buttons to control playback","color":"yellow"}]
