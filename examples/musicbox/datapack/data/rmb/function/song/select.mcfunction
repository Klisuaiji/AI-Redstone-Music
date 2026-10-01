# /trigger play set <编号>
scoreboard players operation #cur mb_cfg = @s mb_song
execute if score #max mb_cfg matches 0 run title @s actionbar "还没有添加歌曲（用 scripts/add_to_musicbox.py 注册）"
execute if score #max mb_cfg matches 1.. if score #cur mb_cfg > #max mb_cfg run tellraw @s ["",{"text":"[音乐盒] ","color":"gold"},{"text":"没有这首歌。当前曲目编号 1~","color":"yellow"},{"score":{"name":"#max","objective":"mb_cfg"}},{"text":"，可 /trigger menu 打开菜单点选","color":"gray"}]
execute if score #max mb_cfg matches 1.. if score #cur mb_cfg matches 1.. if score #cur mb_cfg <= #max mb_cfg run function rmb:song/play
