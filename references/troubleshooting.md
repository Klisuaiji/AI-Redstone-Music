# Troubleshooting: from "no sound" to "it plays"

Run the health check first — it tells you item by item what is wrong and how to fix it:

```bash
python3 scripts/doctor.py --pack <datapack directory or zip> --mc-version <version> \
    --namespace minecraft --song <song name> --song-id <number> --speed 80
```

`doctor.py` is a troubleshooting guide for humans; `validate_pack.py` is the hard gate for CI (it must pass before delivery).
Causes are listed below by symptom — **the order is the troubleshooting order**; if an earlier step fails, do not look at the later ones.

---

## 1. It does not appear in `/datapack list` at all

| Cause | Symptom | Fix |
|---|---|---|
| `pack.mcmeta` is not in the root directory | the whole pack is ignored | unzip the zip and check whether there is an extra nested folder; the datapack root must contain `pack.mcmeta` directly |
| `pack.mcmeta` JSON is invalid | the list shows "broken or incompatible" | common traps: trailing commas, Chinese quotation marks, BOM. Verify with `python3 -m json.tool pack.mcmeta` |
| Wrong version syntax | shows "incompatible" on 26.2 | ≥1.21.9 (format ≥82) must use the `[major,minor]` arrays of `min_format`/`max_format`; writing `pack_format` is **not allowed**, and writing the decimal `107.1` is **not allowed**. Generating with `make_datapack.py` avoids this |
| Version number out of range | a newer version refuses to load a lower-version pack | an older game has a lower `max_format`; for cross-version work align with the table in `references/datapack.md` |

## 2. It is in the list, but `namespace:path` does not show up in `/function` completion

| Cause | Fix |
|---|---|
| **The directory name has a missing or extra s**: since 1.21 it is `data/<ns>/function/`, while 1.14–1.20.6 uses `data/<ns>/functions/` | rename the directory. This mistake **silently loads no functions from the whole pack** and is the most frequent trap |
| No `/reload` after the change | any file change requires `/reload` |
| Path spelled wrong | only what appears in completion is the real path; `path` in `song.json` determines `<ns>:<path>/play` |

## 3. Completion exists, but there is no sound after `/function .../play`

Check in this order (the first two account for 90%):

1. **`tick.json` does not point to this song** — in standalone mode the `values` of `data/minecraft/tags/function/tick.json` must include
   `<ns>:<path>/tick` (for ≤1.20.4 it is `tags/functions/`). Being loaded in the list does not mean it runs every tick.
2. **`#speed nbs_s` is unset or 0** — it is set in `init.mcfunction`. Equivalent to `nbs_s += 0` every tick,
   so all notes pile up on tick 0.
3. **`song_id` does not match** — the `music_type` set by `play.mcfunction` must equal the N in
   `if score ... music_type matches N` in `tick.mcfunction`.
4. **The player carries the `no_music` tag** — the `playsound` selector is `@a[tag=!no_music]`.
5. **In the wrong world/dimension** — functions are per-save, so switching saves means reinstalling.

> Just want to confirm "is it running at all": the simplest way other than `--tick-rate` is `/scoreboard players get music_progress nbs_s`;
> while playing, this value should be growing.

## 4. It plays, but the speed is wrong

| Symptom | Cause |
|---|---|
| slower/faster by an **integer multiple** | the host's `#speed nbs_s` differs from the one used when producing. This convention requires `#speed 80`; anything produced with `--tick-rate 80` must also type `/tick rate 80` in game |
| 4× slower than expected | the timeline was made with `--tick-rate 80`, but the world is still at 20 tps. `/tick rate 80` **resets when you quit and rejoin**, so it must be typed every session |
| drifts over time | server overload (the log shows `Can't keep up!`). Reduce the load or switch to a lighter song |
| the whole song is 2× faster/slower | mistaking `t=` for seconds. `t` is a game tick (1/20 second) |

## 5. Individual notes are wrong

| Symptom | Cause | Fix |
|---|---|---|
| **A few notes make no sound at all** | the tree leaf was written 2 blocks wide (`b-a<=1`); in the adjacent tick pair `(2k,2k+1)` nothing calls `notes/<t>` for the second tick | use `generate.py` from this repository (1-block-wide leaves); running `validate_pack.py` names them directly |
| The pitch sounds wrong | out-of-range notes are **clamped** to the boundary instead of octave-folded | watch the `WARN` lines of `generate.py` while generating. `midi_to_song.py` folds octaves automatically by default |
| A chord is missing notes | wrong dedup key (deduplicating by tick+instrument swallows chords) | the dedup key must be `(tick, instrument, pitch)` |
| Dense passages are muddy | the 20 tps grid is too coarse (half a tick = 25 ms is the physical floor) | see `recipes.md` §5: `/tick rate 80` refines the grid to 12.5 ms |

## 6. Sound is muddy / clipping / too loud

- **Drums should err on the quiet side**: the hi-hat hits once every 16th note and 0.5 will drown the whole song. Default table: kick 0.6 / snare 0.5 / hi-hat 0.25.
- Too many `playsound`s on the same tick: the MC simultaneous sound limit is 255. In this workflow the measured peak is usually 4–8, very safe; if some tick exceeds 30,
  consider trimming chords.
- Several notes of the same instrument on the same tick stack (they do not replace each other); the more notes in a chord, the louder.

## 7. Misc

| Symptom | Explanation |
|---|---|
| `/reload` spams "objective already exists" | normal. `init.mcfunction` runs `objectives add` every time and it does not affect playback |
| Chaos after `/reload` during playback | leftover state; run `/function .../play` once more |
| Others cannot hear it in multiplayer | this workflow uses `minVolume=1` + relative coordinates, which in theory gives full volume everywhere in the world; if the host changed the `playsound` parameters, check whether `stop`/`play` are overridden by another pack |
| Want to temporarily disable one song | `/scoreboard players set music_progress music_type -1` (clears the song selection); or give the player `no_music` |

## 8. Capability boundaries of this skill (do not promise what cannot be done)

- **Only Java Edition ≥1.13 is supported**. Bedrock has no datapacks/`/function`; say so directly.
- **The timbre is the note block timbre** (16 kinds such as harp/pling/guitar/bass/drums) and it neither can nor should reproduce the original song's timbre.
  Wanting "the original timbre" requires a sampled resource pack + a mod, which is a different technical route (see "Related projects" in the README).
- **Hard pitch-range limits**: note blocks as a whole span F#1–F#7 (MIDI 30–102) and a single instrument only has 25 semitones. A low bass below MIDI 30
  can only be raised an octave; a lead melody spanning more than 25 semitones must be split into parts or octave-folded. All of this is recorded in the arrangement decision report.
- **`/tick rate` exists only in 1.20.3+**, and it speeds up the whole world; there is no vanilla solution on older versions.
- **Do not say "it is audible" without in-game verification**: the static self-check (`validate_pack.py` includes the tree state-machine simulation) can prove that "every note
  triggers exactly once on the correct game tick", and `render_preview.py` lets you get a rough preview first, but **timbre and feel only count once you are in game**.
  At delivery, state honestly how far verification went.
