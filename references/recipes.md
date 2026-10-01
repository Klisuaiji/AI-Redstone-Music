# Common recipes

Each recipe is a complete "follow it and you get the result" procedure. See `SKILL.md` for the tool list.

---

## 1. From MIDI to an installable datapack (all in one go)

```bash
python3 scripts/scan_midi.py song.mid                       # 1. health check: parts/pitch range/grid/verdict
python3 scripts/midi_to_song.py song.mid -o song.json \      # 2. automatic arrangement + decision report
    --name mysong --song-id 9 --mc-version 26.2 --report arrangement_notes.md
python3 scripts/render_preview.py song.json -o preview.wav   # 3. preview once (no need to open the game)
python3 scripts/make_datapack.py song.json -o out/mysong \   # 4. assemble the datapack + zip
    --mc-version 26.2
python3 scripts/validate_pack.py --pack out/mysong \         # 5. hard gate
    --namespace minecraft --song mysong --song-id 9 --speed 80 --mc-version 26.2
```

Install into the save's `datapacks/` → `/reload` → `/function minecraft:music/mysong/play`.

## 2. Integrating into an existing lemon-family host datapack

Applies to: the user already has a music datapack that runs each song's `tick` every tick and selects songs with `music_type`.

1. `midi_to_song.py ... --style lemon` (or ignore `style` after generation, since only the song folder is taken)
2. `python3 scripts/generate.py song.json -o out/music/<song name>`
3. Copy all of `out/music/<song name>/` into the host pack under `data/<host namespace>/function/music/`
   (1.20.4 and below use `functions/`)
4. Three conditions must match the host, otherwise the whole song silently fails:
   - the host's `#speed nbs_s` must = **80** (`/scoreboard players get #speed nbs_s`)
   - `song_id` must not conflict with songs the host already has (`lemon` itself occupies 8)
   - the host must run `function <ns>:music/<song name>/tick` every tick
5. Do **not** bring this song's `init.mcfunction`, `pack.mcmeta` or `tags/` into the host pack.

> When delivering only the song folder, `validate_pack.py --pack <song folder>` can self-check too (it does not require `pack.mcmeta`).

## 3. Song chaining (automatically play the next song when one finishes)

Set `"next_song": "minecraft:music/<next song>/play"` in `song.json`, and the generated `stop.mcfunction` will end with
`function minecraft:music/<next song>/play`. When modifying a single song, do **not** touch the host's `main`/`tick` tags.

## 4. Multiple songs coexisting / a menu

- Each song gets one `song_id` and one `path`, independent of the others; only one plays at a time (playing several at once mixes them).
- Selecting a song means assigning to the `music_type` of the fake player `music_progress`: `/scoreboard players set music_progress music_type <id>`;
  that is exactly what `play.mcfunction` does, plus zeroing `nbs_s` and resetting `nbs_t`.
- For menu/jukebox interaction (right-click to change songs, pause, lyrics), see the
  `data/minecraft/function/music/box/` set in the finished pack `examples/RedstoneMusicBox-v3.zip`.

## 5. Advanced precision: using `/tick rate` to refine the time grid 4×

This workflow's grid is "1 t = 1 game tick". At vanilla 20 tps that is **50 ms**, so a 144 BPM sixteenth note
(104.17 ms) can only be quantized to 2 or 3 ticks, with a maximum error of **25 ms** (half a tick, the physical floor).

**MC 1.20.3+ has `/tick rate`**; running the world at 80 tps gives **1 t = 12.5 ms** under the same `#speed 80` convention, and the
quantization error shrinks by the same 4×:

```bash
python3 scripts/midi_to_song.py song.mid -o song.json --tick-rate 80 --name mysong --song-id 9
# measured (a 166-second song at 144 BPM): maximum quantization error 25.0 ms → 4.6 ms
```

In game you must type `/tick rate 80` **manually** once (this workflow will not, and should not, change global settings for you):

| Things you must tell the user | Explanation |
|---|---|
| this speeds up the **whole world** | redstone, mob AI, crop growth and mob spawning all get faster together |
| **not preserved across sessions** | quitting and rejoining the world returns to 20, so it must be retyped every time; forgetting = the whole song is 4× slower |
| a server that cannot keep up will drift | when the log shows `Can't keep up!` the actual TPS has already dropped |
| remember `/tick rate 20` afterwards | restore the original speed |

Production advice: **ship packs at 20 tps by default** (anyone can load them), and treat 80 tps as an advanced option "for when the user explicitly asks for precision".

## 6. Do not want the tree? Schedule directly with `/schedule` (an alternative playback engine)

The tree's advantage is full compatibility with lemon-family hosts and only one branch walked per tick. If you only need a **standalone datapack** and want to
save the per-tick cost, you can schedule directly with `/schedule` after generation (**available only in 1.14+**; not automated in this repository, an advanced manual step):

```
# play_sched.mcfunction (t is that note's game tick)
schedule function minecraft:music/mysong/notes/12 12t
schedule function minecraft:music/mysong/notes/15 15t
...
```

- Pros: no `tick.json`, no `#speed`, zero per-tick cost, and timing is scheduled precisely by the engine.
- Cons: thousands of `schedule` commands pushed into one function at once; `stop` needs a line-by-line `schedule clear <function>`;
  incompatible with hosts that need `#speed`.
- Safety limit: the command limit of a single mcfunction is 65536 (relaxed in 1.20.2+), and this workflow's song sizes (thousands) are very safe.

## 7. No Python environment: assembling the pack by hand

Assemble from the skeletons in `templates/`: choose one of the two `pack.mcmeta` variants (depending on the version), `init.mcfunction`, the two tags,
then drop in the output of `generate.py`. **Three things must be consistent** (syntax / directory name / tag path);
see `templates/README.md` for details. For the rules of generating mcfunctions by hand see `references/format_spec.md` §A, §D.

## 8. When the audio is not MIDI

This skill only eats **MIDI / .nbs projects / text scores**. With only an mp3, transcribe it to MIDI yourself first (external tools such as
basic-pitch, piano_transcription_inference), and **honestly tell the user that quality will drop**:
pure piano solos work best, while vocal or multi-instrument mixes are often painful. After transcribing, run `scan_midi.py` to see the verdict;
if notes are fragmented or parts are chaotic, you should advise the user to find a native MIDI rather than forcing it.

## 9. Delivery checklist (go through it every time)

```
[ ] song.json (a reproducible arrangement input)
[ ] arrangement decision notes (midi_to_song.py --report generates them automatically: part mapping/folding/quantization error/spot checks)
[ ] datapack directory or zip (produced by make_datapack.py, with pack.mcmeta syntax and directory names already matched to the version)
[ ] validate_pack.py all green (including "every notes file referenced exactly once" + the tree state-machine simulation)
[ ] doctor.py all [OK]
[ ] preview wav (render_preview.py, optional but recommended)
[ ] the delivery notes state clearly: the #speed assumption, whether /tick rate was used, which notes were octave-folded, and how far verification went
```
