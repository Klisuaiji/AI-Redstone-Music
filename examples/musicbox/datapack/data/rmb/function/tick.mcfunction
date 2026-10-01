# ==================== 红石音乐盒 · 每刻主循环 ====================
# 1. 玩家指令 → 内部状态
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

# 2. 唱片机与交互实体维护（含丢弃回收 / 自动补发 / 点击采集）
function rmb:box/loop

# 3. 点击判定（单击 / 双击 / 长按）
function rmb:box/click

# 4. 维度禁播
function rmb:dim/check

# 5. 歌词
function rmb:lrc/tick

# 6. 执行排队的全局动作（每刻最多一次，避免多人同时操作时重复执行）
execute if score #act mb_cfg matches 1 run function rmb:box/next
execute if score #act mb_cfg matches 2 run function rmb:box/prev
execute if score #act mb_cfg matches 3 run function rmb:box/pause
scoreboard players set #act mb_cfg 0

# 7. 歌曲进度（暂停或处于禁播维度时，nbs_s 不推进 = 音乐停住）
execute if score #pau mb_cfg matches 0 if score #dim_any mb_cfg matches 0 if score music_progress music_type matches 1.. run function rmb:song/tick
