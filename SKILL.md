---
name: mc-redstone-music
description: >-
  Convert a song (MIDI / .nbs project / text score) into a vanilla-playable Minecraft Java Edition
  mcfunction note block music datapack, with both standalone-datapack and lemon-compatible delivery.
  Use when the user asks to "make redstone music", "turn this song into Minecraft music", "MIDI to
  mcfunction", "generate a note block music datapack", "play this song with commands", or for a
  "note block music datapack", "MIDI to Minecraft datapack", "convert a song into a Minecraft
  datapack", "make a song that plays in vanilla MC". Also matches the same request in other
  languages — answer in the user's language, whatever it is. Examples: Chinese "做红石音乐" /
  "把这首歌做成我的世界音乐" / "MIDI 转 mcfunction" / "生成音符盒音乐数据包" / "红石音乐盒",
  Japanese "Minecraft で音符ブロック音楽を作る" / "MIDI をデータパックに変換",
  Korean "마인크래프트 음악 데이터팩 만들기", Spanish "música de bloques de nota en Minecraft",
  Russian "музыка из нотных блоков в Minecraft". Covers 1.13 through 26.x (including the two
  generations of pack.mcmeta syntax, the function/functions directory-naming boundary, and the
  /tick rate precision upgrade).
---

# Minecraft redstone music mcfunction workflow

Turn a song into a datapack that plays in **vanilla Minecraft Java Edition** with `/function` (note block sounds, no mods, no resource pack required).

## Rules

0. **Language follows the user.** Ask questions, explain, report and deliver in whatever language the
   user wrote in — the repo being English does not mean answering in English. Keep code, commands,
   file paths and identifiers as they are. (Note the separate policy below: a datapack's *in-game*
   text has its own language; the shipped music box uses Chinese.)
1. Only **Minecraft Java Edition ≥ 1.13** is supported (datapacks only exist from 1.13). Bedrock has no `/function`: state that plainly and stop.
2. Every instrument/sound ID must come from the `references/instruments.md` whitelist and must be available in the target version (pling/bit/banjo require 1.14+, trumpet requires 26.1+).
3. **Never make up what you do not know**: if you cannot listen to the audio, say so and ask for MIDI / .nbs / a text score instead. With only an mp3, disclose the transcription quality gap honestly per `references/recipes.md` §8.
4. **There is exactly one verified timeline convention**: `time_unit=nbs_s_units` + `#speed nbs_s = 80` (in which case `t` in song.json is the game tick). If the host's `#speed` is not 80, you must re-time the timeline and explain it; never carry it over as-is.
5. **You must run the self-check before delivery**, and **never claim it "plays" without real in-game verification** (see "Delivery rules" below).

## Delivery rules (read this first — it is the most common mistake)

You must keep apart what a static self-check can prove and what it cannot:

| Evidence | What it proves | How to get it |
|---|---|---|
| `validate_pack.py` all green | every `notes/<t>` is referenced by the tree exactly once, all tree nodes are reachable, instruments/pitch range/pitch/CRLF/tags/song_id are all compliant, **and a tree state-machine simulation proves "every note triggers exactly once at game tick == t"** | mandatory |
| the wav from `render_preview.py` | pitch relationships, rhythm and part balance are roughly right (the timbre is not the in-game timbre) | recommended |
| listening inside the game | timbre, feel, and whether it stutters — **the only final verdict** | disclose honestly in the delivery notes |

- **Do not** say "it already plays / it is installed" without having entered the game. The correct wording is:
  "static self-check all green (including the tree state-machine simulation) + preview wav generated; **not confirmed by listening in-game**".
- **Do not** turn "the datapack loads" into "the music plays".
- Any compromise you made — octave folding, deleted tracks, changed volumes — must be written into the arrangement decision notes. **Do not gloss over it.**

## Tool overview (`scripts/`, all zero-dependency, standard library only)

| Script | When to use it | In one line |
|---|---|---|
| `scan_midi.py` | Step 2: health-check the MIDI first | part list / pitch range / drum-kit GM histogram / rhythm grid / quantization error / one-line verdict |
| `midi_to_song.py` | Steps 3 and 4: automatic arrangement | track classification → instrument mapping → volume table → timeline quantization → octave folding → dedup, producing song.json **+ an arrangement decision report** |
| `nbs_to_json.py` | the source is an .nbs project | OpenNBS / classic .nbs → song.json |
| `generate.py` | Step 5: generate mcfunction | song.json → `play/stop/tick/notes/tree` (tree-window scheduling, an algorithm compared file by file against the lemon reference pack) |
| `validate_pack.py` | Step 5: hard gate (for CI) | tree↔notes consistency + reachability + whitelist/pitch range/CRLF/tags + **tree state-machine simulation** |
| `make_datapack.py` | Step 6: assemble the deliverable | song.json → installable datapack + zip; **automatically picks the right generation of pack.mcmeta syntax and directory name for the target version** |
| `render_preview.py` | preview before delivery | song.json → WAV (simple synthesized timbre, no need to open the game) |
| `doctor.py` | when something goes wrong | a per-item checkup for "why is there no sound", with a fix under every ✗ |
| `add_to_musicbox.py` | to install a song into the Redstone Music Box | register/remove songs, automatically maintaining the song table, the song menu and the song-name subtitles; supports one-step from `.mid` + `.lrc` lyrics |
| `check_refs.py` | after changing a datapack | generic static checks: whether every function reference resolves, JSON validity, CRLF |

All-in-one:

```bash
python3 scripts/scan_midi.py song.mid
python3 scripts/midi_to_song.py song.mid -o song.json --name <song name> --song-id <id> \
    --mc-version <version> --report arrangement-notes.md
python3 scripts/render_preview.py song.json -o preview.wav
python3 scripts/make_datapack.py song.json -o out/<song name> --mc-version <version>
python3 scripts/validate_pack.py --pack out/<song name> --namespace minecraft --song <song name> \
    --song-id <id> --speed 80 --mc-version <version>
```

No Python environment: assemble it by hand following `templates/`; the rules are in `references/format_spec.md` §A/§D and `templates/README.md`.

## Step 1: you must ask the user (all of these are required)

1. **MC Java version** (e.g. 1.20.4 / 1.21.8 / 26.2) — it determines the available instruments, the directory name (`functions` vs `function`), the pack.mcmeta syntax, and whether `/tick rate` can be used.
2. **Source form**: MIDI / MusicXML / OpenNBS project / text score? (for audio, disclose honestly per §8)
3. **Part selection**: keep the lead melody / drums / harmony / bass? Each track can be included/excluded individually.
4. **Deliverable**: song.json / an mcfunction folder / a complete installable datapack zip? Multiple choices allowed.
5. **Integration mode**: A. **lemon-compatible** — the user already has a music datapack and you deliver only the song folder;
   B. **standalone datapack** — it ships with its own init/tick tags, so dropping it into `datapacks/` just works (`make_datapack.py` handles this);
   C. **install into the Redstone Music Box** — when the user wants that jukebox + song menu + lyrics + per-dimension playback ban interaction, use `add_to_musicbox.py` to register the song into the framework in `examples/musicbox/` (see "Step 6").
6. lemon-compatible mode asks additionally: **song_id** (a number unused in the host; the original lemon pack occupies 8), **namespace/path**, and the host's **`#speed nbs_s`** value (`/scoreboard players get #speed nbs_s`). **If it is not 80 you must re-time the timeline.**

## Step 2: analyze the source

```bash
python3 scripts/scan_midi.py song.mid --json report.json
```

It reports: tempo/duration, per track (name · channel · program number · note count · pitch range · octave distribution), the drum-kit GM histogram, the rhythm grid and quantization error, and a **part-mapping verdict**. Read the verdict to the user and set the arrangement plan from it.

MIDI field traps (see `references/midi_notes.md` for details): count note-on only, do not trust the header format, route parts by track name, and do not force a 16th-note grid (many transcriptions use a humanized 1/100-beat grid).

For mixed sources (MIDI accompaniment + audio vocals) you must verify BPM alignment first (`references/midi_notes.md` §3).

## Step 3: arrangement (source parts → note block instruments)

```bash
python3 scripts/midi_to_song.py song.mid -o song.json --name <song name> --song-id <id> \
    --mc-version <version> --report arrangement-notes.md
```

Automatic rules (overridable by flags): drum channels/drum keywords → basedrum 0.6 / snare 0.5 / hat 0.25; names containing bass → `bass`; the remaining tracks are split into lead melody/chords by `--lead-split` (default 72), and `--lead-inst auto` prefers the instrument that can hold the entire track.

Principles:

- Lead melody: `pling` (bright electric piano) / `flute` (high-octave supplement) / `bit` (synth) / `harp` (warm midrange).
  **A single instrument spans only 25 semitones**; if the span is wider, split it by register or fold an octave (both get recorded in the report).
- Bass: `bass`; chords: `guitar` / `banjo`; high accents: `bell` / `chime` / `xylophone`;
  for brass use only the `trumpet` family on 26.1+. Head instruments (1.20+) have no notion of pitch and **must never be used for melody**.
- Default mix volumes (calibrated by ear): lead vocal/accompaniment 1.0, bass 1.0, bit 0.5, kick 0.6, snare 0.5, hi-hat 0.25.
  **Drums should err on the quiet side** — dense hi-hats at 0.5 will drown the whole song.
- Chords on the same tick with the same instrument **must be kept**; dedup is only by `(tick, instrument, pitch)`.
- Pitch range: `use-count = MIDI − instrument base ∈ [0,24]` (see `references/pitch.md`). When out of range, prefer switching to an instrument whose octave fits; if it still does not fit, shift by an octave and **record it in the delivery notes**. MC's simultaneous-sound cap is 255, and the measured peak is 4–8, comfortably safe.

## Step 4: write song.json

For the schema see `references/format_spec.md` §B, for the skeleton `templates/song.template.json`.
Set `meta.mc_version` to the user's version; use `time_unit` = `nbs_s_units` + `speed` (default 80).

## Step 5: generate and self-check

```bash
python3 scripts/generate.py song.json -o out/music/<song name>          # lemon-compatible deliverable
python3 scripts/make_datapack.py song.json -o out/<song name> --mc-version <version>   # standalone datapack + zip
python3 scripts/validate_pack.py --pack out/<song name> --namespace <ns> --song <song name> \
    --song-id <id> --speed 80 --mc-version <version>
```

Self-check list (`validate_pack.py` covers all of it):

- **Every `notes/<t>.mcfunction` is referenced exactly once by the tree** — a leaf must be **1 block wide**; a 2-block-wide leaf leaves the second tick's file in an adjacent tick pair `(2k,2k+1)` called by nobody (**permanently silent**), and also makes notes fire 1 game tick early.
  For details and measured data see `references/format_spec.md` §A.
- All tree nodes are reachable from the root and there are no dangling child nodes; the tree root name in `tick.mcfunction` matches tree/.
- Instruments are inside the version whitelist, `pitch ∈ [0.5, 2.0]`, `use-count ∈ [0,24]`.
- The `song_id` matches across `play/stop/tick`; the last tick chains into `stop`; every `.mcfunction` is CRLF.
- Standalone mode: the directory name follows the `function`/`functions` boundary, pack.mcmeta follows the version-appropriate syntax, and the tick/load tag paths are correct.

## Step 6: delivery

- **Standalone datapack**: drop the zip produced by `make_datapack.py` into `datapacks/` → `/reload` →
  `/function <ns>:<path>/play`; give a player the `no_music` tag to mute it.
- **Install into the Redstone Music Box**: `python3 scripts/add_to_musicbox.py --box <box dir> --song song.json --name "<song name>" [--lrc lyrics.lrc]`
  → `/reload`. The box provides the jukebox (left click = previous song / press-and-hold = pause / right click = next song / double right click = menu), `/trigger lrc` lyrics,
  `/trigger play set <id>` song selection, and per-dimension playback bans. See `examples/musicbox/README.md` for details.
  **Language note:** the shipped box's *in-game* text is Chinese (it targets a Chinese-speaking player
  base) while its code comments are English — do not "helpfully" translate the in-game strings unless
  the user asks for a different in-game language. `add_to_musicbox.py` generates the Chinese text for
  you; its console output and the generated comments stay English.
- **lemon-compatible**: deliver the `<song name>/` folder (play/stop/tick/tree/notes) plus integration notes: put it into
  `data/<ns>/function/` (1.21+) or `functions/` (≤1.20.4); confirm the host runs this song's `tick` every tick,
  that `#speed nbs_s = 80`, and that `song_id` does not collide. **Do not** bring `pack.mcmeta` / `init` / `tags` into the host pack.
- Attach `song.json` + the arrangement decision notes (auto-generated by `--report`) + the preview wav (optional).
- State clearly in the delivery notes: the `#speed` assumption, whether `/tick rate` was used, which octaves were folded, and **how far verification went**.

## Version terrain quick reference (decides "how far this version can go")

| Version | Directory name | pack.mcmeta | Instrument count | `/tick rate` precision upgrade |
|---|---|---|---|---|
| 1.13 | `functions/` | `pack_format` | 10 | none (only from 1.20.3) |
| 1.14–1.20.2 | `functions/` | `pack_format` | 16 | none |
| 1.20.3–1.20.6 | `functions/` | `pack_format` | 16 | ✅ `/tick rate 80` works (grid 12.5 ms) |
| 1.21–1.21.8 | `function/` (singular!) | `pack_format` | 16 | ✅ |
| ≥1.21.9 (incl. 26.x) | `function/` | **`min_format`/`max_format` = `[major,minor]`**, cannot use `pack_format`, cannot use a decimal `107.1` | 16 (26.1+ has 4 more brass instruments) | ✅ |

Full format number table and the two generations of syntax: `references/datapack.md`. `make_datapack.py` picks the right one automatically per version.

## Reference files

| File | Contents |
|---|---|
| `references/format_spec.md` | Output specification (line-by-line rules for play/stop/tick/tree/notes) + song.json schema + manual generation notes |
| `references/instruments.md` | Instrument whitelist (version/pitch range/bottom block/sound event) |
| `references/pitch.md` | `use-count ↔ /playsound pitch` conversion table |
| `references/datapack.md` | Full pack_format table, two generations of pack.mcmeta syntax, directory-naming boundary, runtime facts |
| `references/midi_notes.md` | MIDI parsing field traps, BPM alignment, mix volumes, **consistency self-check before delivery** |
| `references/troubleshooting.md` | Symptom → cause → fix, from "no sound" to "it plays" |
| `references/recipes.md` | Common recipes: integrating into a lemon host, song chaining, multiple songs coexisting, **the /tick rate precision upgrade**, /schedule as an alternative engine |
| `templates/` | song.json skeleton + standalone datapack skeleton (for hand assembly) |
| `examples/musicbox/` | **The Redstone Music Box general framework** (no songs included): jukebox + song menu + lyrics + per-dimension playback ban; register songs with `add_to_musicbox.py` |
| `examples/demo.mid` | An 8-bar sample MIDI for quickly validating the toolchain |

## Reference artifacts and self-check

- `examples/musicbox/`: a **general framework datapack** (songs not included), also usable as a comparison for "what the output should look like";
  it was extracted from the same author's finished v3 pack, with identical interaction mechanics.
- `tests/smoke_test.py`: end-to-end regression test (including the regression case "a 2-block-wide leaf must be caught", and the whole flow of "registering a song into the music box");
  `python3 tests/smoke_test.py` should print `SMOKE TEST PASSED`.
- When something goes wrong, first run `python3 scripts/doctor.py --pack <pack>`.
