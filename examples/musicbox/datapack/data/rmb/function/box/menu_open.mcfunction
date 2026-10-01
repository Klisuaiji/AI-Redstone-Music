# Open the song menu (clickable in chat)
tag @s add mb_menu
tellraw @s ["",{"text":"========== ♪ Song menu ==========","color":"gold","bold":true}]
function rmb:box/menu_list
tellraw @s ["",{"text":"Tip: ","color":"gray"},{"text":"click a song name to play it; double right click again to close the menu; /trigger lrc toggles lyrics","color":"dark_gray"}]
