# ==================== Redstone Music Box · per-tick main loop ====================
# 1. Player commands → internal state
execute as @a[scores={menu=1..}] run function rmb:box/toggle
execute as @a[scores={lrc=1..}] run function rmb:lrc/toggle
execute as @a[scores={play=1..}] run scoreboard players operation @s mb_song = @s play
execute as @a[scores={play=1..}] run function rmb:song/select
scoreboard players reset @a menu
scoreboard players reset @a lrc
scoreboard players reset @a play
scoreboard players enable @a menu
scoreboard players enable @a lrc
scoreboard players enable @a play

# 2. Music box and interaction entity maintenance (drop recovery / auto re-issue / click capture)
function rmb:box/loop

# 3. Click detection (single click / double click / hold)
function rmb:box/click

# 4. Per-dimension playback ban
function rmb:dim/check

# 5. Lyrics
function rmb:lrc/tick

# 6. Run the queued global action (at most once per tick, so simultaneous actions are not repeated)
execute if score #act mb_cfg matches 1 run function rmb:box/next
execute if score #act mb_cfg matches 2 run function rmb:box/prev
execute if score #act mb_cfg matches 3 run function rmb:box/pause
scoreboard players set #act mb_cfg 0

# 7. Song progress (while paused or in a banned dimension nbs_s does not advance = the music stops)
execute if score #pau mb_cfg matches 0 if score #dim_any mb_cfg matches 0 if score music_progress music_type matches 1.. run function rmb:song/tick
