================ 红石音乐盒（通用框架 · MC 26.2）================
本包不含任何歌曲：它是一个「播放器 + 点歌菜单 + 歌词 + 维度禁播」的盒子，
歌曲由 scripts/add_to_musicbox.py 注册进来（每首歌放在 data/rmb/function/song/<编号>/）。

【安装】把 zip 丢进存档 datapacks/ → /reload

【玩家指令】
  /trigger menu             获取 / 收回 唱片机（附魔，不可放置、不可丢弃，丢了自动补发）
  /trigger lrc              开关歌词（显示在动作栏 = 屏幕下方的小字，随音乐切换）
  /trigger play set <编号>   点歌；也可以 /function rmb:play {song:歌名}

【唱片机操作】
  左键单击        = 上一首
  连击 / 长按左键 = 暂停 · 播放
  右键单击        = 下一首
  双击右键        = 打开 / 关闭点歌菜单（聊天栏里点歌名即可播放）

【管理指令（/function）】
  rmb:dim/ban       禁止在「执行者所在维度」播放
  rmb:dim/unban     解除执行者所在维度的禁播
  rmb:dim/status    查看禁播状态
  rmb:dim/clear     解除全部维度禁播
  rmb:dim/on|off    维度禁播功能总开关
  rmb:uninstall     卸载（清物品 / 清交互实体 / 删记分板）

【添加歌曲】
  python3 scripts/add_to_musicbox.py --box <本数据包目录> --song song.json [--lrc 歌词.lrc]
  （也可以直接给 .mid，脚本会先自动编曲）
  加完要 /reload 才生效。

【记分板（全部是缩写）】
  menu / lrc / play                                      玩家 trigger
  mb_song mb_lyc mb_pls mb_rct mb_hol mb_hct mb_don
  mb_uct mb_udo mb_msg mb_cfg                            内部状态
  music_type / nbs_s / nbs_t                             歌曲播放约定（不要改名）

【版本】需要 MC 1.21.5+（用到 items entity 物品谓词与组件语法）；本包 pack.mcmeta 按 26.2 写。
        换版本请按 references/datapack.md 改 pack.mcmeta 的格式号与目录名。
