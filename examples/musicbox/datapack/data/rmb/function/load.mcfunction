# ==================== 红石音乐盒 · 加载 ====================
# 记分板命名（全部缩写）：
#   menu / lrc / play              —— 玩家指令（trigger）
#   mb_*                           —— 内部状态
#   music_type / nbs_s / nbs_t     —— 歌曲播放约定，不要改名！本 skill 生成的歌曲依赖这三个

# --- 歌曲播放约定 ---
scoreboard objectives add music_type dummy
scoreboard objectives add nbs_s dummy
scoreboard objectives add nbs_t dummy
scoreboard players set #speed nbs_s 80

# --- 玩家指令 ---
scoreboard objectives add menu trigger
scoreboard objectives add lrc trigger
scoreboard objectives add play trigger

# --- 内部状态 ---
scoreboard objectives add mb_song dummy
scoreboard objectives add mb_lyc dummy
scoreboard objectives add mb_pls dummy
scoreboard objectives add mb_rct dummy
scoreboard objectives add mb_hol dummy
scoreboard objectives add mb_hct dummy
scoreboard objectives add mb_don dummy
scoreboard objectives add mb_uct dummy
scoreboard objectives add mb_udo dummy
scoreboard objectives add mb_msg dummy
scoreboard objectives add mb_cfg dummy

# --- 配置默认值（假玩家都在 mb_cfg 上）---
scoreboard players set #pau mb_cfg 0
scoreboard players set #ban mb_cfg 1
scoreboard players set #dim_o mb_cfg 0
scoreboard players set #dim_n mb_cfg 0
scoreboard players set #dim_e mb_cfg 0
scoreboard players set #dim_any mb_cfg 0
scoreboard players set #max mb_cfg 0
scoreboard players set #cur mb_cfg 0
scoreboard players set #act mb_cfg 0
scoreboard players set @a mb_msg 0

# --- 允许玩家使用 trigger（trigger 用掉后会失效，所以每刻都要重新 enable）---
scoreboard players enable @a menu
scoreboard players enable @a lrc
scoreboard players enable @a play

# --- 载入提示 ---
title @a title "已成功加载音乐数据包"
title @a subtitle "输入 /trigger menu 获取红石音乐盒"
tellraw @a ["",{"text":"[音乐盒] ","color":"gold","bold":true},{"text":"已成功加载音乐数据包","color":"white"},{"text":"（通用框架，尚未添加歌曲）","color":"dark_gray"},{"text":"\n  /trigger menu","color":"yellow"},{"text":" 获取 / 收回唱片机","color":"gray"},{"text":"\n  /trigger lrc","color":"yellow"},{"text":" 开关歌词","color":"gray"},{"text":"\n  /trigger play set <编号>","color":"yellow"},{"text":" 点歌（也可点菜单里的歌名）","color":"gray"}]

# --- 曲目表（由 scripts/add_to_musicbox.py 维护）---
function rmb:song/max
