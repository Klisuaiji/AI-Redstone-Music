# 双击右键：开/关菜单
execute if entity @s[tag=mb_menu] run function rmb:box/menu_close
execute unless entity @s[tag=mb_menu] run function rmb:box/menu_open
