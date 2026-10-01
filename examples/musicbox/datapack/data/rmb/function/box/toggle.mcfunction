# /trigger menu —— 有就收回，没有就发一个（以 @s 执行）
# 注意：clear 之后就不能再用「有没有物品」判断了，所以用 mb_tmp 标签先记住状态
tag @s remove mb_nogive
tag @s remove mb_tmp
execute if items entity @s inventory.* minecraft:jukebox[custom_data~{musicbox:1b}] run tag @s add mb_tmp
execute if entity @s[tag=mb_tmp] run clear @s minecraft:jukebox[custom_data~{musicbox:1b}] 1
execute if entity @s[tag=mb_tmp] run tag @s add mb_nogive
execute if entity @s[tag=mb_tmp] run title @s title "红石音乐盒已收回"
execute if entity @s[tag=mb_tmp] run title @s actionbar "再输入一次 /trigger menu 可重新领取"
execute unless entity @s[tag=mb_tmp] run function rmb:box/give
execute unless entity @s[tag=mb_tmp] run title @s title "已获得 红石音乐盒"
execute unless entity @s[tag=mb_tmp] run title @s actionbar "左键 上一首 | 长按左键 暂停/播放 | 右键 下一首 | 双击右键 菜单"
execute unless entity @s[tag=mb_tmp] run scoreboard players set @s mb_msg 60
tag @s remove mb_tmp
