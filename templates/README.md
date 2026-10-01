# Templates

Skeletons for when you don't want to run the scripts and would rather assemble the files by hand.
**If you can run the scripts, don't assemble by hand** — `make_datapack.py` automatically picks the right
`pack.mcmeta` syntax and directory name for the target version (the two spots that historically break most often).

| File | Purpose |
|---|---|
| `song.template.json` | song.json skeleton: 4 parts + a note for every field (keys starting with an underscore are comments and are ignored) |
| `standalone/pack.mcmeta.26.2.json` | `pack.mcmeta` for ≥1.21.9 (`min_format`/`max_format`, `[major,minor]` integer arrays) |
| `standalone/pack.mcmeta.1.21.8.json` | `pack.mcmeta` for ≤1.21.8 (`pack_format` integer) |
| `standalone/init.mcfunction` | scoreboard objectives + `#speed nbs_s` (required in standalone mode) |
| `standalone/tags_load.json` | → `data/minecraft/tags/function/load.json` (`tags/functions/` on ≤1.20.4) |
| `standalone/tags_tick.json` | → `data/minecraft/tags/function/tick.json` |

## Assembling a standalone datapack by hand

```
<datapack name>/
├── pack.mcmeta                                  ← pick one of the two above by version
└── data/
    ├── <namespace>/
    │   └── function/                            ← functions/ on ≤1.20.4
    │       └── music/<song name>/               ← generate.py's -o output (play/stop/tick/notes/tree)
    │           └── init.mcfunction              ← use standalone/init.mcfunction
    └── minecraft/
        └── tags/function/                       ← tags/functions/ on ≤1.20.4
            ├── load.json                        ← values points to <namespace>:music/<song name>/init
            └── tick.json                        ← values points to <namespace>:music/<song name>/tick
```

These three things must agree with each other, otherwise the whole pack silently fails:
1. The `pack.mcmeta` syntax must match the target version (≥1.21.9 uses `min_format`/`max_format`, and you must not write a decimal such as `107.1`)
2. The directory name must match the version (≥1.21 singular `function/`, 1.14–1.20.6 plural `functions/`) — **one missing `s` and the whole pack won't load**
3. Tag paths are written `<namespace>:<path>`, **without** `function/` and **without** `.mcfunction`

Run a validation pass after assembling:

```bash
python3 scripts/validate_pack.py --pack <datapack name> --namespace <namespace> --song <song name> --song-id <id> --speed 80 --mc-version <version>
python3 scripts/doctor.py       --pack <datapack name> --mc-version <version> --song <song name> --song-id <id>
```

For the matching format numbers and the boundary between them, see [`references/datapack.md`](../references/datapack.md).
