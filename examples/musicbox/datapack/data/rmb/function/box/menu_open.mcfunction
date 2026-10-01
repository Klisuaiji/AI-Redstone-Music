# Open the song menu (clickable in chat)
tag @s add mb_menu
tellraw @s ["",{"text":"========== ♪ 点歌菜单 ==========","color":"gold","bold":true}]
function rmb:box/menu_list
tellraw @s ["",{"text":"提示：","color":"gray"},{"text":"点歌名即可播放；再双击右键关闭菜单；/trigger lrc 开关歌词","color":"dark_gray"}]
