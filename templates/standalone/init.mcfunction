# Standalone-mode initialization (called by tags/function/load.json on /reload)
# Note: when the objective already exists, add reports "already exists" — that is normal and does not affect playback
scoreboard objectives add music_type dummy
scoreboard objectives add nbs_s dummy
scoreboard objectives add nbs_t dummy
# #speed = the increment the host adds to nbs_s every tick. 80 → t in song.json is the game tick (the tree window 80×t goes with it)
scoreboard players set #speed nbs_s 80
