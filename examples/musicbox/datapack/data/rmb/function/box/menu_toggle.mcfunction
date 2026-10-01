# Double right click: open/close the menu
execute if entity @s[tag=mb_menu] run function rmb:box/menu_close
execute unless entity @s[tag=mb_menu] run function rmb:box/menu_open
