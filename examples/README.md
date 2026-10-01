# 示例数据包:红石音乐盒 v2

仓库自带的**可直接安装**的完整数据包(`RedstoneMusicBox-v2.zip`,42,543 个文件),
兼容 **Minecraft Java 1.21.2–1.21.8 / 26.2**(pack_format 57–107.1)。

它同时是本 skill 的参考产物:生成器的树调度、play/stop/tick、`#speed nbs_s 80`
时轴约定均以本包(及其前代 lemon 系数据包)为准。

## 安装

1. 将 zip 放入存档的 `datapacks` 文件夹(`.minecraft/saves/<存档>/datapacks/`)
2. 进入世界后 `/reload`
3. 聊天栏提示「已成功加载音乐数据包」后,输入 `/trigger menu` 领取红石音乐盒

## 操作

| 操作 | 效果 |
|---|---|
| `/trigger menu` | 领取/再领红石音乐盒(附魔唱片机,不可放置不可丢弃,丢弃自动补发) |
| 手持唱片机 · 左键单击 | 上一首 |
| 手持唱片机 · 左键长按 | 暂停 / 继续 |
| 手持唱片机 · 右键单击 | 下一首 |
| 手持唱片机 · 右键双击 | 打开/关闭点歌菜单 |
| `/trigger lyc` | 歌词显示开/关(《After the Rain》含 43 句歌词,字幕随音乐切换) |
| `/trigger song set 0-10` | 按编号点歌 |
| `/trigger mb_<歌名> set 1` | 每首歌专属 trigger |

## 曲目库(11 首)

| 编号 | 歌曲 | | 编号 | 歌曲 |
|---|---|---|---|---|
| 0 | kagec3 | | 6 | badapple |
| 1 | sanyaose | | 7 | lunatic |
| 2 | touhoukami | | 8 | popcorn |
| 3 | lemon | | 9 | UN |
| 4 | After the Rain(雨停时分) | | 10 | shanghaitea |
| 5 | baka | | | |

编号即 `/trigger song set` 的取值;`music_type=17` 为《雨停时分》。
原播放链 lemon → After the Rain → baka 已保留,切歌/暂停/恢复均原生联动。

## 管理功能

```
/function minecraft:music/box/remove      删除唱片机
/function minecraft:music/box/dim_ban     禁播执行者所在维度
/function minecraft:music/box/dim_unban   解除禁播
/function minecraft:music/box/dim_status  查看禁播名单
/function minecraft:music/box/ban_enable  启用禁播(默认)
/function minecraft:music/box/ban_disable 关闭禁播
```

## 结构要点(给开发者)

- 计分板:宿主约定 `music_type` / `nbs_s` / `nbs_t`,`#speed nbs_s = 80`(note tick = 游戏 tick);
  音乐盒子系统另有 `mb_*` 系列 trigger/dummy 目标
- 每刻链:`minecraft:music/main` → box/tick + lrc_tick + dim_check + 各曲 tick(暂停/禁播时跳过)
- 歌曲目录:`data/minecraft/function/music/<歌名>/{play,stop,tick,notes,tree}`
- 26.2 兼容:`supported_formats` 上限 107.1,`function/` 目录命名(1.21+)
