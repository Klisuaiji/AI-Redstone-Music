# Datapack version essentials (wiki "Data pack")
## pack.mcmeta pack_format table
1.13–1.14.4=4 | 1.15–1.16.1=5 | 1.16.2–1.16.5=6 | 1.17=7 | 1.18–1.18.1=8 | 1.18.2=9 |
1.19–1.19.3=10 | 1.19.4=12 | 1.20–1.20.1=15 | 1.20.2=18 | 1.20.3–1.20.4=26 |
1.20.5–1.20.6=41 | 1.21–1.21.1=48 | 1.21.2–1.21.3=57 | 1.21.4=61 | 1.21.5=71 |
1.21.6=80 | 1.21.7–1.21.8=81 | 1.21.9–1.21.10=88.0(includes a minor version number) | 1.21.11=94.1 | 26.1=101.1 | 26.2=107.1 | 26.3=121.0
(A pack loads as long as the minimum required pack_format ≤ the target version; packs for newer versions are refused by older games)

## The two generations of pack.mcmeta syntax (datapack format 82 = the 1.21.9 boundary, important)
- Target **≤1.21.8 (format ≤81)**: write `pack_format` (`supported_formats` optional)
- Target **≥1.21.9 (format ≥82, including 26.1/26.2/26.3)**: you **must** write the two `[major,minor]` integer arrays `min_format` + `max_format`,
  and `pack_format` / `supported_formats` **must not** appear any more; you **must not** write decimals either (❌ `107.1` → ✅ `[107,1]`)
- To support both sides of 82: provide all four fields, and `min_format[0]` must equal the minimum of `supported_formats`
- The old style that writes only `pack_format` is judged incompatible on ≥1.21.9 (upstream RedstoneMusicBox-v3 uses exactly this
  cross-boundary hybrid, `pack_format:57` + `supported_formats:{min:57,max:107.1}`, and is missing min/max_format)
- 26.2 example: `{"pack":{"min_format":[107,1],"max_format":[107,1],"description":"<song name> Redstone Music"}}`

## The directory-naming boundary (1.21 = the 24w21a rename)
- ≤1.20.4: `data/<ns>/functions/xxx.mcfunction`, tag `data/<ns>/tags/functions/tick.json`
- ≥1.21:   `data/<ns>/function/xxx.mcfunction`,  tag `data/<ns>/tags/function/tick.json`

## Minimal standalone-mode skeleton
```

pack.mcmeta                        {"pack":{"pack_format":<table above>,"description":"<song name> Redstone Music"}}      # ≤1.21.8
                                   for targets ≥1.21.9 change to {"pack":{"min_format":[major,minor],"max_format":[major,minor],"description":"..."}}
data//function/music//play.mcfunction ... (output of generate.py)
data//function/music/init.mcfunction
scoreboard objectives add music_type dummy
scoreboard objectives add nbs_s dummy
scoreboard objectives add nbs_t dummy
scoreboard players set #speed nbs_s 2
data//tags/function/tick.json  {"values":[":music//tick"]}   # ≤1.20.4 uses tags/functions/
data//tags/function/load.json  {"values":[":music/init"]}

```
Playback: /function <ns>:music/<song>/play; give a player the `no_music` tag to mute it.

## Integration (lemon-compatible) mode prerequisites
The user's datapack must already have: the scoreboard objectives music_type/nbs_s/nbs_t; the fake player #speed (on nbs_s); a per-tick execution of each song's tick.mcfunction; and a playback chain that selects songs with music_type=<song_id>. The deliverable only needs the song directory, and song_id must not conflict.

## Runtime facts
- /playsound: <sound> <source> <targets> [pos] [volume] [pitch] [minVolume]; JE pitch ∈ [0.5,2.0]
- volume is the "audible radius multiplier" (1 = 16 blocks) and does not amplify loudness; lemon uses minVolume=1 + relative coordinates so that players anywhere in the world hear it at full volume
- The simultaneous sound limit is 255 (wiki "Sound"); overly dense chords must be trimmed
- 1.20.2+ function macros start with $, do not use them in this workflow; the 1.18+ scoreboard name length limit has been relaxed, so music_progress (14 characters) is safe on all versions
