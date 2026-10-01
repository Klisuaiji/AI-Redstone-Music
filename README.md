# RedstoneMusic Skill (AI redstone music)

Turn a song into an mcfunction note block music datapack that plays in **vanilla Minecraft Java Edition**.
No mods, no resource pack — drop it into `datapacks/`, `/reload`, `/function`, and it plays.

> The generator algorithm was reverse-engineered from the lemon reference pack (970 mcfunction files) and corrected by comparing it file by file;
> the whole pipeline has been validated on real delivery cases (12 songs, a datapack of 46,000 mcfunction files).
> **Every script is zero-dependency**, using only the Python standard library.

## What this is (30 seconds)

- **What it does**: you give it a **MIDI** (or an `.nbs` project / a text score) and it produces a **datapack**;
  type `/function <namespace>:music/<song name>/play` in the game and it starts playing.
- **What you need**: Minecraft **Java Edition ≥ 1.13** (vanilla is enough, no mods) + the ability to type a few commands. That is all.
- **What it sounds like**: note block timbres (harp/electric piano/flute/guitar/bass/drums…). It does **not** replicate the original song's timbre —
  wanting "the original timbre" is a different technical route (see "Related projects" below).
- **How it differs from "building a redstone machine"**: this project takes the **command datapack** route (`playsound` triggers note block samples),
  and does not build physical note block machines. Zero footprint, extremely low performance cost, works in any world.

## Quick start

Put the whole `mc-redstone-music/` directory into your skills directory, then tell the AI:

> Use mc-redstone-music to turn this song into redstone music

The AI will confirm in order: MC version → source form → part selection → deliverable → integration mode (lemon-compatible requires a song_id and the host's
`#speed`) → generate and self-check.

You can also run the command line yourself (all-in-one, all zero-dependency):

```bash
python3 scripts/scan_midi.py song.mid                                  # 1. health check + verdict
python3 scripts/midi_to_song.py song.mid -o song.json \                 # 2. automatic arrangement + decision report
    --name mysong --song-id 9 --mc-version 26.2 --report arrangement-notes.md
python3 scripts/render_preview.py song.json -o preview.wav              # 3. listen once first (no need to open the game)
python3 scripts/make_datapack.py song.json -o out/mysong \              # 4. assemble datapack + zip
    --mc-version 26.2
python3 scripts/validate_pack.py --pack out/mysong --namespace minecraft \   # 5. hard gate
    --song mysong --song-id 9 --speed 80 --mc-version 26.2
```

To try it with the sample MIDI included in the repository:

```bash
python3 scripts/scan_midi.py examples/demo.mid
python3 tests/smoke_test.py            # end-to-end regression test, should print SMOKE TEST PASSED
```

## Toolchain (`scripts/`)

| Script | Purpose |
|---|---|
| `scan_midi.py` | MIDI health check: parts/pitch range/drum kit/rhythm grid/quantization error + a **one-line verdict** (which tracks to keep, which instrument to map them to) |
| `midi_to_song.py` | MIDI → song.json automatic arrangement (classify→map→volume→quantize→fold octaves→dedup) + an **arrangement decision report** |
| `nbs_to_json.py` | OpenNBS / classic `.nbs` → song.json |
| `generate.py` | song.json → `play/stop/tick/notes/tree` (tree-window scheduled playback) |
| `validate_pack.py` | Pre-delivery hard gate: consistency + reachability + whitelist/pitch range + **tree state-machine simulation** (proving every note triggers exactly once at the right game tick) |
| `make_datapack.py` | Assemble an installable datapack + zip; **automatically picks the right generation of pack.mcmeta syntax and directory name for the target version** |
| `render_preview.py` | song.json → WAV preview (simple synthesized timbre) |
| `doctor.py` | Troubleshooting wizard: from "no sound" to "it plays", with a fix under every ✗ |

## Delivery rules (important)

| Evidence | What it proves |
|---|---|
| `validate_pack.py` all green | structure, pitch range and timeline are **all compliant**; every note triggers **exactly once** at game tick == t |
| the wav from `render_preview.py` | pitch relationships/rhythm/part balance are roughly right |
| **listening inside the game** | timbre and feel — **the only final verdict** |

If you have not entered the game, do not say "it plays". See "Delivery rules" in [`SKILL.md`](SKILL.md) for details.

## Compatible versions

| Item | Range |
|---|---|
| Generation target | Minecraft Java **1.13+** (incl. 26.x) |
| Directory naming | `function/` (singular) from 1.21; 1.14–1.20.6 uses `functions/` (plural) |
| pack.mcmeta | ≤1.21.8 uses `pack_format`; **≥1.21.9 uses the `[major,minor]` array of `min_format`/`max_format`** (a decimal `107.1` is not allowed) |
| Precision upgrade | **1.20.3+** can use `/tick rate 80` to refine the time grid from 50 ms to 12.5 ms (error 25 ms → 4.6 ms, measured) |
| Not supported | Bedrock Edition (no datapacks/`/function`) |

## Workflow (six steps)

1. **Ask**: version / source / part selection / deliverable / integration mode / song_id and `#speed`
2. **Analyze the source**: `scan_midi.py`; for mixed sources verify BPM alignment first
3. **Arrange**: `midi_to_song.py`; part→instrument mapping + mix volume table (lead vocal/accompaniment 1.0, kick 0.6, snare 0.5, hi-hat 0.25)
4. **Write song.json**: for the schema see `references/format_spec.md`, for the skeleton `templates/song.template.json`
5. **Generate and self-check**: `generate.py` / `make_datapack.py` + `validate_pack.py`
6. **Deliver**: zip + song.json + arrangement decision notes (and state clearly how far verification went)

See [`SKILL.md`](SKILL.md) for details.

## Redstone Music Box (general framework datapack)

[`examples/musicbox/`](examples/musicbox/) is a general-purpose player box that **contains no songs at all**: drop it into `datapacks/`,
register songs into it with `add_to_musicbox.py`, and you get a complete music box.

| Need | Implementation |
|---|---|
| Get / recall the jukebox | `/trigger menu` (enchanted jukebox; **cannot be placed**, **cannot be dropped**, automatically re-issued if lost) |
| Previous song / next song | left click / right click |
| Pause · play | double click / long press left click |
| Song menu | double right click → a clickable song-name list in chat (or `/trigger play set <id>`) |
| Select a song by name | `/function rmb:play {song:"<song name>"}` |
| Lyrics | `/trigger lrc` toggle, shown in the action bar, switching line by line with the music (standard `.lrc` import supported) |
| Per-dimension playback ban | `/function rmb:dim/ban` (run once while standing in the dimension to ban), plus `status` / `unban` / `clear` / `on` / `off` |
| Load notice | after `/reload` the screen shows "已成功加载音乐数据包" |
| Scoreboard | all abbreviations: `menu` `lrc` `play` + `mb_*` (`music_type` / `nbs_s` / `nbs_t` are the song playback convention, kept under their original names for compatibility with songs generated by this skill) |

> **Language:** the repository (docs, comments, tool output) is English, but the **in-game text is
> Chinese** — the music box targets a Chinese-speaking player base. Every player-visible string
> (`tellraw` / `title` / item name / pack description) is Chinese; every code comment is English.
> See [`examples/musicbox/README.md`](examples/musicbox/README.md) for the details.

```bash
cp -r examples/musicbox/datapack /tmp/box
python3 scripts/add_to_musicbox.py --box /tmp/box --song song.mid --name "<song name>" --lrc lyrics.lrc
python3 scripts/check_refs.py /tmp/box      # static checks: function references / JSON / line endings
```

For details (scoreboard cross-reference table, the contract for adding songs by hand, how the interaction is implemented, known limitations) see
[`examples/musicbox/README.md`](examples/musicbox/README.md). Requires **MC 1.21.5+**; this pack is packaged for 26.2.

## Related projects (a different technical route)

[**Cohenjikan/McMusicMaker**](https://github.com/Cohenjikan/McMusicMaker) builds **physical note block machines**:
with the RedPiano mod + a sampled resource pack it actually builds note blocks/redstone machines in the world (shapes such as `inplace` / `swave` / `multilane`),
depending on Fabric, `/tick rate 80` and a resource pack; the timbre is sampled piano (closer to the original song), but the footprint is large and it needs mods.

|  | This project (datapack) | McMusicMaker (physical machines) |
|---|---|---|
| Dependencies | none (vanilla) | Fabric + RedPiano mod + sampled resource pack |
| Sound | 16 note block timbres | sampled piano etc. (103 timbres) |
| Footprint | 0 | grows with song length |
| Playback | `/function .../play` | press a button after building the machine in the world |
| Versions | 1.13+ | see its `docs/VERSION_TACTICS.md` |

The two routes do not conflict: for "zero dependencies, play it anywhere" choose this project; for "physical machines + the original timbre" choose McMusicMaker.
This project's `/tick rate` precision upgrade also drew on that route's quantization experience.

## Repository structure

```
SKILL.md                       # AI skill entry point: rules, delivery rules, tool overview, six-step workflow
README.md                      # this file
CHANGELOG.md                   # changelog
references/
  format_spec.md               # output specification + song.json schema + manual generation notes
  instruments.md               # instrument whitelist (version/pitch range)
  pitch.md                     # use-count ↔ /playsound pitch conversion table
  datapack.md                  # full pack_format table, two generations of pack.mcmeta syntax, directory-naming boundary, runtime facts
  midi_notes.md                # practical MIDI parsing and alignment experience + pre-delivery consistency self-check
  troubleshooting.md           # symptom → cause → fix
  recipes.md                   # common recipes (incl. the /tick rate precision upgrade and /schedule as an alternative engine)
scripts/
  scan_midi.py                 # MIDI health-check report
  midi_to_song.py              # MIDI → song.json automatic arrangement
  nbs_to_json.py               # .nbs → song.json
  generate.py                  # song.json → mcfunction (tree/notes/play/stop/tick)
  validate_pack.py             # pre-delivery self-check (incl. tree state-machine simulation)
  make_datapack.py             # assemble a standalone datapack + zip (two generations of pack.mcmeta)
  add_to_musicbox.py           # register songs into the Redstone Music Box (song table / menu / lyrics)
  check_refs.py                # generic static checks: function references / JSON / CRLF
  render_preview.py            # song.json → WAV preview
  doctor.py                    # no-sound troubleshooting wizard
  midilib.py                   # shared MIDI reading library
templates/
  song.template.json           # song.json skeleton (with field descriptions)
  standalone/                  # standalone datapack skeleton (two generations of pack.mcmeta + init + tags)
tests/
  smoke_test.py                # end-to-end regression test (incl. the "2-block-wide leaf goes silent" regression case)
  gen_demo_midi.py             # generates examples/demo.mid
examples/
  musicbox/                    # Redstone Music Box: general framework datapack + zip + docs (no songs)
  demo.mid                     # 8-bar sample MIDI
  song.example.json            # minimal song.json example
  RedstoneMusicBox-v3.zip      # companion finished product: Redstone Music Box v3 (12 songs + player)
```

## Timeline convention (important)

A lemon-family host executes `nbs_s += #speed` every tick, and the tree window is `80×tick`.
**With `#speed nbs_s = 80`, note tick = game tick** (1 t = 1/20 second).
Before integrating into another datapack, confirm its `#speed`, otherwise the timeline must be re-timed.

**Precision upgrade (1.20.3+)**: after typing `/tick rate 80` in the game, under the same convention 1 t = 12.5 ms and the
quantization error shrinks 4×. The cost is that the whole world speeds up, it resets on re-entering the world, and it drifts when the server is overloaded — see
[`references/recipes.md`](references/recipes.md) §5.

## Notes

- This repository is for learning and exchange; the tracks it contains are conversions by the respective redstone music community, and the copyright belongs to the original composers
- The generated music uses note block synthesized timbres and cannot and will not replicate the original song's timbre
- Bedrock Edition is not supported
