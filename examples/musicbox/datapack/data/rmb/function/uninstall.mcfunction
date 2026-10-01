# /function rmb:uninstall —— full uninstall (clear items, entities and scoreboards)
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
tellraw @a ["",{"text":"[MusicBox] ","color":"gold"},{"text":"Uninstalled (music_type / nbs_s / nbs_t used for song playback are kept so running songs are not affected)","color":"yellow"}]
