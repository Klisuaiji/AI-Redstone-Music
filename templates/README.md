# 模板

不想跑脚本、要手工拼文件时用这里的骨架。**能跑脚本就别手拼**——`make_datapack.py` 会自动按目标版本
选对 `pack.mcmeta` 写法与目录名（历史上最容易错的两处）。

| 文件 | 用途 |
|---|---|
| `song.template.json` | song.json 骨架：4 个声部 + 每个字段的中文说明（以下划线开头的键是注释，会被忽略） |
| `standalone/pack.mcmeta.26.2.json` | ≥1.21.9 的 `pack.mcmeta`（`min_format`/`max_format`，[主,次] 整数数组） |
| `standalone/pack.mcmeta.1.21.8.json` | ≤1.21.8 的 `pack.mcmeta`（`pack_format` 整数） |
| `standalone/init.mcfunction` | 记分板目标 + `#speed nbs_s`（独立模式必需） |
| `standalone/tags_load.json` | → `data/minecraft/tags/function/load.json`（≤1.20.4 是 `tags/functions/`） |
| `standalone/tags_tick.json` | → `data/minecraft/tags/function/tick.json` |

## 手工拼一个独立数据包

```
<数据包名>/
├── pack.mcmeta                                  ← 按版本选上面两个之一
└── data/
    ├── <命名空间>/
    │   └── function/                            ← ≤1.20.4 用 functions/
    │       └── music/<歌名>/                     ← generate.py 的 -o 输出（play/stop/tick/notes/tree）
    │           └── init.mcfunction              ← 用 standalone/init.mcfunction
    └── minecraft/
        └── tags/function/                       ← ≤1.20.4 用 tags/functions/
            ├── load.json                        ← values 指向 <命名空间>:music/<歌名>/init
            └── tick.json                        ← values 指向 <命名空间>:music/<歌名>/tick
```

三处必须自洽，否则整包静默失效：
1. `pack.mcmeta` 的写法要和目标版本匹配（≥1.21.9 用 `min_format`/`max_format`，且不能写小数 `107.1`）
2. 目录名和版本匹配（≥1.21 单数 `function/`，1.14–1.20.6 复数 `functions/`）——**少一个 s 整包不加载**
3. 标签里的路径写法是 `<命名空间>:<路径>`，**不带** `function/`、**不带** `.mcfunction`

拼完跑一遍自检：

```bash
python3 scripts/validate_pack.py --pack <数据包名> --namespace <命名空间> --song <歌名> --song-id <编号> --speed 80 --mc-version <版本>
python3 scripts/doctor.py       --pack <数据包名> --mc-version <版本> --song <歌名> --song-id <编号>
```

对应格式数字与分水岭见 [`references/datapack.md`](../references/datapack.md)。
