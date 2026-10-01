# /function rmb:uninstall —— 彻底卸载（清物品、清实体、清记分板）
kill @e[type=interaction,tag=mb_box]
clear @a minecraft:jukebox[custom_data~{musicbox:1b}]
scoreboard objectives remove menu
scoreboard objectives remove lrc
scoreboard objectives remove play
scoreboard objectives remove mb_song
scoreboard objectives remove mb_lyc
scoreboard objectives remove mb_pls
scoreboard objectives remove mb_rct
scoreboard objectives remove mb_hol
scoreboard objectives remove mb_hct
scoreboard objectives remove mb_don
scoreboard objectives remove mb_uct
scoreboard objectives remove mb_udo
scoreboard objectives remove mb_msg
scoreboard objectives remove mb_cfg
tellraw @a ["",{"text":"[音乐盒] ","color":"gold"},{"text":"已卸载（歌曲播放用的 music_type / nbs_s / nbs_t 保留，避免影响正在运行的歌曲）","color":"yellow"}]
