# /function rmb:play {song:"song_name"}  —— request a song by name (macro, 1.20.2+)
$data modify storage rmb:io arg set value {song:"$(song)"}
scoreboard players set #cur mb_cfg 0
function rmb:song/by_name
execute if score #cur mb_cfg matches 1.. run function rmb:song/play
execute if score #cur mb_cfg matches 0 run title @s actionbar "Song not found; /trigger menu opens the menu"
