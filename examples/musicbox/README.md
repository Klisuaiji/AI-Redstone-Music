# 红石音乐盒（通用框架数据包）

一个**不含任何歌曲**的通用播放器：附魔唱片机 + 点歌菜单 + 歌词 + 维度禁播。
歌曲通过 `scripts/add_to_musicbox.py` 注册进来，播放逻辑复用本 skill 的时轴约定
（`music_type` / `nbs_s` / `nbs_t` + `#speed nbs_s = 80`），所以 `generate.py` 产出的歌能直接放进来。

| 文件 | 说明 |
|---|---|
| `datapack/` | 数据包源文件树（可直接改，改完重压或整个文件夹丢进 `datapacks/`） |
| `redstone-musicbox.zip` | 同一份数据包的安装包（40 个文件，17 KB），zip 根目录即 `pack.mcmeta` |

## 安装

1. 把 `redstone-musicbox.zip` 丢进存档的 `datapacks/`
2. `/reload` → 屏幕中央显示「已成功加载音乐数据包」
3. `/trigger menu` 拿到红石音乐盒

## 玩家用法

| 操作 | 效果 |
|---|---|
| `/trigger menu` | 获取唱片机；**再输一次收回**（收回后不会自动补发） |
| `/trigger lrc` | 开关歌词（显示在动作栏 = 屏幕下方的小字，随音乐逐句切换） |
| `/trigger play set <编号>` | 点歌（编号见菜单） |
| `/function rmb:play {song:"歌名"}` | 按歌名点歌 |
| 左键单击 | 上一首 |
| 连击 / 长按左键 | 暂停 · 继续 |
| 右键单击 | 下一首 |
| 双击右键 | 打开 / 关闭点歌菜单（聊天栏里点歌名直接播放） |

唱片机是**附魔的唱片机**物品：

- **不可放置** —— 真放下去了会被 `advancement`（`musicbox/placed`）捕获并清掉方块
- **不可丢弃** —— 按 Q 丢出的物品会被立即回收，然后自动补发一个新的
- **丢失自动补发** —— 死亡、被 `clear` 掉都会补；主动 `/trigger menu` 收回的不会补

> 单击类操作有约 0.85 秒（17 刻）的判定延迟：这是为了区分"单击"和"连击/长按"，
> 手感上是"按一下，稍等一下才切歌"。左键连击与长按都判为暂停/继续。

## 管理指令（`/function`）

| 指令 | 作用 |
|---|---|
| `rmb:dim/ban` | 禁止在**执行者所在维度**播放（走到那个维度里执行一次即可） |
| `rmb:dim/unban` | 解除执行者所在维度的禁播 |
| `rmb:dim/clear` | 解除全部维度禁播 |
| `rmb:dim/status` | 查看当前禁播状态 |
| `rmb:dim/on` / `rmb:dim/off` | 维度禁播功能总开关 |
| `rmb:uninstall` | 卸载：清唱片机、清交互实体、删记分板 |

只要**有任意一个非旁观玩家**处在被禁播的维度，全服音乐就会停住（`nbs_s` 不再推进），
离开后自动继续 —— 和暂停是同一套机制，所以歌词、进度都会跟着停。

## 添加歌曲

```bash
# 从 song.json 注册（自动分配下一个编号）
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack --song song.json --name "歌名"

# 直接从 MIDI 一步到位，顺便带歌词
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack \
    --song 歌曲.mid --name "Lemon" --lrc 歌词.lrc

# 指定编号 / 查看 / 移除
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack --song song.json --id 3
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack --list
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack --remove 3
```

加完**必须 `/reload`**（新增的是新的函数文件）。脚本会自动维护这四样东西：

```
data/rmb/function/song/max.mcfunction        曲目数量（#max）
data/rmb/function/song/name.mcfunction       "♪ 正在播放：X" 字幕
data/rmb/function/song/by_name.mcfunction    歌名 → 编号
data/rmb/function/box/menu_list.mcfunction   可点击的点歌菜单
```

### 手动添加的契约

不想用工具也可以手工放：每首歌一个目录 `data/rmb/function/song/<编号>/`，必须有四个文件：

| 文件 | 内容 |
|---|---|
| `play.mcfunction` | `scoreboard players set music_progress music_type <编号>` + 把 `nbs_s` 清 0、`nbs_t` 重置为 -1 |
| `tick.mcfunction` | 每刻推进 `nbs_s += #speed nbs_s` 并调度音符（`generate.py` 的产物） |
| `stop.mcfunction` | 归零 `nbs_s`、`reset nbs_t`；建议末尾 `function rmb:song/ended` 实现自动下一首 |
| `lrc.mcfunction` | 歌词；**必须有这个文件**（没歌词就只写一行注释），否则每刻都会报函数不存在 |

编号必须**连续从 1 开始**（`next` / `prev` 按 `1..max` 循环）。用工具注册时它会保证这一点。

## 记分板（全部是缩写）

| 名称 | 类型 | 用途 |
|---|---|---|
| `menu` / `lrc` / `play` | trigger | 玩家指令。trigger 用一次就会失效，所以每刻都会重新 `enable` |
| `mb_song` | dummy | 玩家刚输入的曲目编号（`/trigger play set N`） |
| `mb_lyc` | dummy | 歌词开关的中间变量 |
| `mb_pls` | dummy | 左键脉冲（1 刻） |
| `mb_rct` | dummy | 右键点击数 |
| `mb_hol` `mb_hct` `mb_don` | dummy | 左键状态机：单击 / 连击（长按）/ 冷却 |
| `mb_uct` `mb_udo` | dummy | 右键状态机：单击 / 双击 |
| `mb_msg` | dummy | 临时消息期间的"歌词压制"倒计时 |
| `mb_cfg` | dummy | 假玩家配置：`#pau`(暂停) `#ban`(禁播总开关) `#dim_o/n/e` `#dim_any` `#max`(曲目数) `#cur`(选中编号) `#act`(排队的动作) |
| `music_type` / `nbs_s` / `nbs_t` | dummy | **歌曲播放约定**，与本 skill 生成的歌曲互通，不要改名 |

## 版本要求

**MC 1.21.5+**。用到的较新特性：

- `execute if items entity …`（物品谓词）与 `custom_data` / `enchantments` / `item_name` 组件语法 —— **1.21.5+**
- `interaction` 实体（采集左右键）—— 1.19.4+
- 函数宏（`$function rmb:song/$(id)/tick`，用于按编号派发）—— 1.20.2+
- `return 0` —— 1.20.2+

本包 `pack.mcmeta` 按 **26.2**（数据包格式 `[107,1]`）写。要用于其他版本，按
[`../../references/datapack.md`](../../references/datapack.md) 改格式号与目录名即可。

## 实现原理（维护时看这里）

| 机制 | 做法 |
|---|---|
| 左右键识别 | 每个玩家身边跟一个 `interaction` 实体（`tag=mb_box`）。手持盒子时贴着眼睛、否则浮在头顶 2 格（不挡正常挖方块）。每刻轮询它的 `attack`（左键）/ `interaction`（右键）NBT，读完就 `data remove` |
| 单击 vs 长按 | 17 刻判定窗：窗口内再次触发 = 连击/长按，窗口结束仍只有一次 = 单击 |
| 不可放置 | `advancement/musicbox/placed.json`（`minecraft:placed_block` + 物品组件过滤）→ `rmb:box/placed` 把刚放的方块设成空气 |
| 不可丢弃 | 每刻扫描附近 `item` 实体，命中就 `kill`，下一行逻辑再补发一个新的 |
| 物品标记 | `custom_data={musicbox:1b}`，检测用 `minecraft:jukebox[* custom_data~{musicbox:1b}]` |
| 按编号派发 | `execute store result storage rmb:io arg.id …` + `$function rmb:song/$(id)/tick`（宏），所以**不需要**给每首歌写一行注册代码 |
| 暂停 / 禁播 | 全局 `#pau` / `#dim_any`；一旦成立就跳过歌曲 `tick`，`nbs_s` 自然停住 |
| 歌词时间轴 | 用 `nbs_s`（每刻都推进、暂停跟着停），而不是音符才更新的 `nbs_t` |

## 已知限制

- 多人同时点击时，切歌/暂停是**全局**的（同一台音乐盒 = 同一个声音），这是刻意的设计
- 曲目编号必须连续；用 `--remove` 删掉中间编号后要 `/reload`，编号不会自动补位（可用 `--id` 填洞）
- 卸载（`rmb:uninstall`）故意保留 `music_type` / `nbs_s` / `nbs_t`，避免打断其他正在用它们的音乐数据包
- 未在游戏内实机验证过（本仓库的开发环境没有 Minecraft）：静态检查见 `scripts/check_refs.py`，
  逻辑对照的是同作者的成品包 `RedstoneMusicBox-v3.zip`（1.21.2–26.2，同一套交互机制）
