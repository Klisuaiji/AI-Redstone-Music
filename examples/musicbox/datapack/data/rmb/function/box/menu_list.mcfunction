# 曲目列表 —— 由 scripts/add_to_musicbox.py 自动生成，不要手改
tellraw @s ["",{"text":"[音乐盒] ","color":"gold"},{"text":"还没有添加歌曲。","color":"yellow"}]
tellraw @s ["",{"text":"  用 ","color":"gray"},{"text":"python3 scripts/add_to_musicbox.py --box <数据包> --song song.json","color":"white"},{"text":" 注册歌曲","color":"gray"}]
tellraw @s ["",{"text":"  注册后这里会出现可点击的歌名。","color":"dark_gray"}]
