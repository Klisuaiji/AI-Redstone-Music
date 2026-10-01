# Redstone Music Box (generic framework datapack)

A generic player that contains **no songs at all**: enchanted jukebox + song menu + lyrics + per-dimension playback ban.
Songs are registered through `scripts/add_to_musicbox.py`, and playback reuses this skill's timeline convention
(`music_type` / `nbs_s` / `nbs_t` + `#speed nbs_s = 80`), so songs produced by `generate.py` drop straight in.

| File | Description |
|---|---|
| `datapack/` | Datapack source tree (edit it directly, then re-zip it or drop the whole folder into `datapacks/`) |
| `redstone-musicbox.zip` | Install package of the same datapack (40 files, 17 KB); the zip root is `pack.mcmeta` |

## Installation

1. Drop `redstone-musicbox.zip` into the world's `datapacks/`
2. `/reload` → "Music datapack loaded successfully" appears in the center of the screen
3. `/trigger menu` to get the Redstone Music Box

## Player usage

| Action | Effect |
|---|---|
| `/trigger menu` | Get the jukebox; **run it again to put it away** (putting it away does not trigger an automatic re-issue) |
| `/trigger lrc` | Toggle lyrics (shown in the action bar = the small text at the bottom of the screen, switching line by line with the music) |
| `/trigger play set <id>` | Pick a song (ids are shown in the menu) |
| `/function rmb:play {song:"song name"}` | Pick a song by its name |
| Left click | Previous song |
| Double click / hold left click | Pause · resume |
| Right click | Next song |
| Double right click | Open / close the song menu (click a song name in chat to play it directly) |

The jukebox is an **enchanted jukebox** item:

- **Cannot be placed** — if you do place it, an `advancement` (`musicbox/placed`) catches it and clears the block
- **Cannot be dropped** — an item thrown with Q is collected immediately, and then a new one is automatically re-issued
- **Automatically re-issued when lost** — dying or being `clear`ed re-issues one; putting it away yourself with `/trigger menu` does not

> Single-click actions have a decision delay of about 0.85 seconds (17 ticks): this is what separates a "single
> click" from a "double click / long press", and it feels like "press once, then wait a moment before the song
> switches". Both a left double click and a long press count as pause/resume.

## Admin commands (`/function`)

| Command | Effect |
|---|---|
| `rmb:dim/ban` | Ban playback in **the dimension the executor is in** (just run it once while you are in that dimension) |
| `rmb:dim/unban` | Lift the playback ban for the dimension the executor is in |
| `rmb:dim/clear` | Lift every per-dimension playback ban |
| `rmb:dim/status` | Show the current ban status |
| `rmb:dim/on` / `rmb:dim/off` | Master switch for the per-dimension playback ban |
| `rmb:uninstall` | Uninstall: clear the jukebox, clear the interaction entities, delete the scoreboards |

As long as **any non-spectator player** is in a banned dimension, music stops across the whole server (`nbs_s` stops
advancing), and it resumes automatically after they leave — this is the same mechanism as pause, so lyrics and
progress stop along with it.

## Adding songs

```bash
# Register from song.json (the next id is allocated automatically)
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack --song song.json --name "song name"

# Straight from MIDI in one step, lyrics included
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack \
    --song song.mid --name "Lemon" --lrc lyrics.lrc

# Pick an id / list / remove
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack --song song.json --id 3
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack --list
python3 scripts/add_to_musicbox.py --box examples/musicbox/datapack --remove 3
```

After adding, **you must `/reload`** (the files added are new function files). The script automatically maintains these four things:

```
data/rmb/function/song/max.mcfunction        song count (#max)
data/rmb/function/song/name.mcfunction       "♪ Now playing: X" subtitle
data/rmb/function/song/by_name.mcfunction    song name → id
data/rmb/function/box/menu_list.mcfunction   clickable song menu
```

### Contract for manual additions

If you would rather not use the tool, you can also place things by hand: one directory per song, `data/rmb/function/song/<id>/`, with four required files:

| File | Content |
|---|---|
| `play.mcfunction` | `scoreboard players set music_progress music_type <id>` + clear `nbs_s` to 0 and reset `nbs_t` to -1 |
| `tick.mcfunction` | Advance `nbs_s += #speed nbs_s` every tick and schedule the notes (produced by `generate.py`) |
| `stop.mcfunction` | Zero `nbs_s`, `reset nbs_t`; it is recommended to end with `function rmb:song/ended` for the automatic next song |
| `lrc.mcfunction` | Lyrics; **this file is required** (with no lyrics, write a single comment line), otherwise every tick reports a missing function |

Ids must be **consecutive starting from 1** (`next` / `prev` cycle over `1..max`). Registering through the tool guarantees this.

## Scoreboards (all abbreviations)

| Name | Type | Purpose |
|---|---|---|
| `menu` / `lrc` / `play` | trigger | Player commands. A trigger stops working after one use, so it is re-`enable`d every tick |
| `mb_song` | dummy | The song id the player just entered (`/trigger play set N`) |
| `mb_lyc` | dummy | Intermediate variable for the lyrics toggle |
| `mb_pls` | dummy | Left-click pulse (1 tick) |
| `mb_rct` | dummy | Right-click count |
| `mb_hol` `mb_hct` `mb_don` | dummy | Left-click state machine: single click / double click (long press) / cooldown |
| `mb_uct` `mb_udo` | dummy | Right-click state machine: single click / double click |
| `mb_msg` | dummy | Countdown for the "lyrics suppression" during a temporary message |
| `mb_cfg` | dummy | Fake player config: `#pau`(pause) `#ban`(playback-ban master switch) `#dim_o/n/e` `#dim_any` `#max`(song count) `#cur`(selected id) `#act`(queued action) |
| `music_type` / `nbs_s` / `nbs_t` | dummy | **Song playback convention**, interoperable with songs generated by this skill; do not rename |

## Version requirements

**MC 1.21.5+**. Newer features used:

- `execute if items entity …` (item predicates) and the `custom_data` / `enchantments` / `item_name` component syntax — **1.21.5+**
- `interaction` entities (to capture left/right clicks) — 1.19.4+
- Function macros (`$function rmb:song/$(id)/tick`, used to dispatch by id) — 1.20.2+
- `return 0` — 1.20.2+

This pack's `pack.mcmeta` is written for **26.2** (datapack format `[107,1]`). To use it on another version, just
change the format number and directory names as described in [`../../references/datapack.md`](../../references/datapack.md).

## Implementation notes (read this when maintaining)

| Mechanism | Approach |
|---|---|
| Left/right click detection | Each player is followed by an `interaction` entity (`tag=mb_box`). While the box is held it sits at eye level, otherwise it floats 2 blocks above the head (it does not block normal block breaking). Every tick it polls that entity's `attack` (left click) / `interaction` (right click) NBT and `data remove`s it after reading |
| Single click vs long press | A 17-tick decision window: triggering again inside the window = double click/long press; when the window closes with still only one trigger = single click |
| Cannot be placed | `advancement/musicbox/placed.json` (`minecraft:placed_block` + item component filter) → `rmb:box/placed` sets the block that was just placed to air |
| Cannot be dropped | Every tick nearby `item` entities are scanned; a hit is `kill`ed and the next line of logic re-issues a new one |
| Item marker | `custom_data={musicbox:1b}`, detected with `minecraft:jukebox[* custom_data~{musicbox:1b}]` |
| Dispatch by id | `execute store result storage rmb:io arg.id …` + `$function rmb:song/$(id)/tick` (macro), so you do **not** need a registration line per song |
| Pause / playback ban | Global `#pau` / `#dim_any`; once either holds, the song's `tick` is skipped and `nbs_s` stops on its own |
| Lyrics timeline | Uses `nbs_s` (advances every tick and stops along with pause) rather than `nbs_t`, which only updates on notes |

## Known limitations

- When several players click at the same time, song switching/pausing is **global** (one music box = one sound); this is deliberate
- Song ids must be consecutive; after deleting a middle id with `--remove` you must `/reload`, ids do not close the gap automatically (use `--id` to fill the hole)
- Uninstall (`rmb:uninstall`) deliberately keeps `music_type` / `nbs_s` / `nbs_t`, so it does not interrupt other music datapacks that are using them
- Not verified on a real in-game client (this repo's development environment has no Minecraft): for static checks see `scripts/check_refs.py`,
  and the logic was compared against the same author's finished pack `RedstoneMusicBox-v3.zip` (1.21.2–26.2, the same interaction mechanism)
