# Changelog

## Unreleased: repository translated to English

The whole repository is now English so the skill is usable internationally. No behaviour changed:
all commands, flags, function paths, objective names, tags, JSON keys, numbers and format tables are
byte-identical — only comments, documentation prose, tool output and in-game text changed.

- Documentation: `SKILL.md` (frontmatter trigger text rewritten as keyword-rich English),
  `README.md`, `CHANGELOG.md`, all seven `references/*.md`, `templates/README.md`,
  `examples/README.md`, `examples/musicbox/README.md`.
- Tools: every docstring, comment, `argparse` help text and printed message in
  `scripts/*.py` and `tests/*.py`; the Markdown arrangement report written by `midi_to_song.py`;
  the comment markers and user-facing text that `make_datapack.py` and `add_to_musicbox.py`
  write into generated datapacks.
- Datapack in-game text: all 35 `.mcfunction` files under `examples/musicbox/datapack/`
  (`[MusicBox]` prefix, load notice, menu, lyrics, errors) plus its `README.txt` and
  `pack.mcmeta` description; `redstone-musicbox.zip` was rebuilt.
- Tests: assertions that looked for Chinese substrings were re-pointed at stable ASCII tokens
  (`verdict`, `silent`, `state-machine`, `ALL CHECKS PASSED`, `[X]`) so they no longer depend on
  wording; the check count is unchanged at 35 and the suite is green.
- Kept on purpose: Chinese *track-name matching aliases* in the MIDI tools are written as `\u`
  escapes with an English comment, so the source stays pure ASCII while MIDI files whose tracks are
  named in Chinese are still classified correctly.
- Not translated: `examples/RedstoneMusicBox-v3.zip` — a released binary build of the v3 product
  whose in-game text is Chinese. It is kept as-is; only the repository source is English.

## Unreleased (Redstone Music Box)

### Added: Redstone Music Box general framework datapack
- `examples/musicbox/`: a general player box that **contains no songs at all** (40 files / 17 KB) + an installable zip.
  - `/trigger menu` gets / recalls the **enchanted jukebox**; it cannot be placed (the advancement clears the block after catching it),
    cannot be dropped (anything that hits the ground is reclaimed immediately), and is automatically re-issued if lost
  - left click = previous song; double click / long press left click = pause · play; right click = next song; double right click = song menu
  - the menu is a clickable song-name list in chat; `/trigger play set <id>` or `/function rmb:play {song:"<song name>"}`
  - `/trigger lrc` toggles lyrics (action bar, switching line by line with the timeline, standard `.lrc` import supported)
  - per-dimension playback ban: `rmb:dim/ban|unban|status|clear|on|off`; `rmb:uninstall` removes everything in one step
  - after `/reload` it shows "Music datapack loaded successfully"
  - all scoreboards are abbreviations: `menu`/`lrc`/`play` + `mb_*`; `music_type`/`nbs_s`/`nbs_t` keep their original names for compatibility with generated songs
  - numbered dispatch is implemented with a **function macro**, so adding a song **does not** require changing any registration code
- `scripts/add_to_musicbox.py`: registers a song.json (or a `.mid` directly) into the box, automatically maintaining the song count, the song-name subtitles,
  the name→number table and the clickable menu; supports `--lrc` lyrics, `--list`, `--remove` and number-collision protection
- `scripts/check_refs.py`: generic static checks (whether function references resolve / JSON validity / CRLF) — run it after changing a datapack
- `tests/smoke_test.py`: added a full-flow case for "registering demo.mid into the music box and validating it"

### Removed
- `examples/datapack_demo/` (the first 16.5s of Dystopia) and `examples/datapack_m3/` (one complete song) have been deleted:
  the repository examples are now a **general framework that contains no songs**. They were artifacts of the generator before the fix; their behavior was still correct,
  but the former had 54 notes firing 1 tick early; when you need a format comparison, just generate one on the spot with the commands in `examples/README.md`.

## Previous version (toolchain)

### Fixed
- **`generate.py` tree leaf bug (silence + early firing)**: the leaf condition used to be `b-a<=1` (2 blocks wide) while only `rng[0]` was emitted.
  The deepest leaves produced by bisection are always the aligned `[2k,2k+1]`, so
  1. when an adjacent tick pair `(2k,2k+1)` both had notes, the `notes/<t>.mcfunction` for `2k+1` was generated but **called by no node at all**
     → that note was permanently silent (measured: 79 of 1169 notes unreachable in one song; in upstream finished packs, 491 in
     `after_the_rain` and 85 in `fanwutuobang`);
  2. the window started from the leaf's left edge, so notes falling in the right half **fired 1 game tick (50 ms) early**
     (measured: 54 of the 117 notes in the upstream example pack `fanwutuobang_demo` fired early).
  Changed to `y == x` (1 block wide): the window/guard formulas are unchanged, the timeline semantics are unchanged, and the tree depth is +1 (that song: 2719 → 3888 nodes).
- `validate_pack.py`: when pointed at a song folder it no longer wrongly requires `pack.mcmeta`.

### New scripts
- `scan_midi.py`: MIDI health check (parts/pitch range/drum kit GM/rhythm grid/quantization error) + a one-line verdict.
- `midi_to_song.py`: MIDI → song.json automatic arrangement (track classification, instrument mapping, volume table, timeline quantization, octave folding, dedup),
  plus a generated **arrangement decision report** (markdown).
- `make_datapack.py`: song.json → installable datapack + zip; automatically picks the right generation of `pack.mcmeta` syntax and directory name for the target version,
  eliminating mistakes like "writing 26.2 as `pack_format` + the decimal `107.1`".
- `render_preview.py`: song.json → WAV preview (no need to open the game).
- `doctor.py`: no-sound troubleshooting wizard (per-item ✓/✗ + fixes + a symptom quick-reference table).
- `midilib.py`: shared MIDI reading library (counts note-on only, routes by track name, tolerant of malformed structures).

### New capabilities
- **`--tick-rate`: precision upgrade**. When the host runs `/tick rate 80`, under the same `#speed 80` convention 1 t = 12.5 ms and the
  quantization error shrinks 4× (measured on a 144 BPM song: maximum error 25.0 ms → 4.6 ms).
- `midi_to_song.py`'s `--lead-inst auto`: if the whole track's pitch range fits a single instrument, it is not split into parts.
- Time-resolution guardrail: when the `#speed`/`tick_rate` combination makes the grid coarser than 100 ms it is rejected outright (unless `--force`).

### New tests and templates
- `tests/smoke_test.py`: end-to-end regression test, including the regression case "changing the tree back to 2-block-wide leaves must be judged FAIL".
- `tests/gen_demo_midi.py` + `examples/demo.mid`: an 8-bar sample MIDI (including same-tick chords and a 1-game-tick flam).
- `templates/`: song.json skeleton + standalone datapack skeleton (two generations of `pack.mcmeta`, init, tags).

### Documentation
- `references/troubleshooting.md`: symptom → cause → fix, from "no sound" to "it plays".
- `references/recipes.md`: common recipes (integrating into a lemon host, song chaining, multiple songs coexisting, the `/tick rate` precision upgrade,
  `/schedule` as an alternative playback engine, hand assembly without a Python environment).
- `SKILL.md`: added "Delivery rules (evidence)", "Tool overview" and "Version terrain quick reference"; the frontmatter trigger words were completed with both Chinese and English.
- `references/datapack.md`: added "The two generations of pack.mcmeta syntax"; corrected the `pack.mcmeta` line in the standalone-mode skeleton.
- `references/format_spec.md`: §A now states that a leaf must be 1 block wide, recording the two side effects and the measured data.
- `references/midi_notes.md`: added section 9, "The consistency self-check that must be done before delivery".
- `README.md`: added the 30-second introduction, the toolchain table, the delivery rules, the related-projects comparison and the `/tick rate` explanation.

## Earlier

- Initial version: `SKILL.md` + `references/` (format specification, instrument whitelist, pitch table, datapack essentials, practical MIDI experience) +
  `scripts/generate.py`, `nbs_to_json.py` + `examples/` (example packs and finished packs).
