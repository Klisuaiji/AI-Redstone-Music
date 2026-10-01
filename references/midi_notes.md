# MIDI parsing and alignment in practice (a real delivery: Dystopia → LobbyMusicPack song_id 16)

This file distills reusable lessons from one complete real delivery (MIDI accompaniment + audio vocal dual source, PowerShell 5.1
with no Python environment, lemon-family host datapack). The format specification still follows format_spec.md.

## 1. Count note-on only, do not rely on note-on/off pairing

A pairing parser records open notes in `dict[channel+pitch]`, and **same-pitch overlaps** (extremely common in guitar/drums) overwrite each other:
the note count is badly undercounted (measured 960→366) and "stuck notes" hundreds of seconds long appear.
Note block music only needs the **onset time** (0x90 vel>0); duration is useless — just walk the note-ons directly.
A "stuck note" (endTick far beyond the song length) = a missing note-off; that track's note-on times are still usable, do not discard the whole track.

## 2. Real-world MIDI structure is messy

- **format 0 carrying multiple MTrk chunks** is illegal but really exists; just parse in chunk order and do not trust the header's format;
- **Route parts by track name (FF 03 meta), not by track index** — deleting one track shifts every index, but the names stay the same
  (real case: after deleting the electric bass track on the user's request, the distorted guitar that was track4 became track3);
- varlen continuation bytes have the high bit = 1 and the terminating byte has the high bit = 0; getting it backwards parses the whole track as garbage;
- running status: when a data byte is preceded by no status byte, reuse the previous status; after F0/F7 running status is cleared;
- Song length check: the seconds converted from the last onset should be close to the audio duration (real case 147.78s ↔ 147.9s).

## 3. BPM alignment verification (mandatory when mixing multiple sources)

MIDI's nominal tempo often disagrees with the reference audio (real case: MIDI 120 BPM, the original song 117 BPM, yet the note times converted
at the file's own 120 line up with the audio). When the accompaniment comes from MIDI and the vocals come from audio analysis, the two timelines must be unified:

1. Extract ground truth from the audio (drum onsets / vocal fundamental frequency);
2. Convert MIDI onsets at each candidate tempo and compute a **match rate** (±60ms) and an **offset histogram** against the ground truth;
3. Clearly higher match rate + offsets concentrated at a constant (e.g. +0.06s, the general lead of onset detection) → adopt that conversion, do not scale any further;
4. An overall offset ≤ 0.06s (≈1 game tick) can be ignored; if the offset is larger, shift everything uniformly.

## 4. Audio onset detection produces false positives; clean MIDI is more trustworthy

Real case: audio extraction detected dense "kick drums" in the 0-10s intro, when they were actually all low piano notes; the clean MIDI drum track shows
the drums only enter at 10.04s (correct). **Use MIDI to correct audio extraction for the drums' entry time and density**; only when MIDI is missing or
corrupt should you fall back to audio extraction, and clean up drum-free passages such as the intro by hand.

## 5. Deduplication rules

**Chords in the same part on the same tick must be kept** (2-4 note chords are common in sampled keyboard/guitar tracks).
The dedup key = (tick, instrument, pitch); deduplicating by (tick, instrument) swallows chords.

## 6. Default mix volumes (calibrated over two rounds of user listening)

| Part | Instrument | vol |
|---|---|---|
| vocal lead melody | pling | 1.0 |
| intro/accompaniment harmony | harp / guitar | 1.0 |
| accents | bit | 0.5 |
| bass | bass | 1.0 |
| kick drum | basedrum | 0.6 |
| snare drum | snare | 0.5 |
| hi-hat/ride | hat | 0.25 |

Experience: drums should **err on the quiet side** by default — the hi-hat hits once every 16th note, and at vol 0.5 "the drums take over the whole sound"
(the user's own words). Dense parts (several playsounds per tick) stack; they do not replace each other.

## 7. How #speed and the tree window go together

A lemon-family host pack runs `nbs_s += #speed` every tick; the tree leaf window is `80*t..80*t+160`.
**When note tick = game tick, #speed must = 80** (measured value from a real pack's load.mcfunction).
When switching hosts, ask about #speed first: if it is ≠80, either re-scale the timeline to its value or state that it is incompatible.
Song chaining (the next song) is done by `function <ns>:<path>/play` in stop.mcfunction; do not touch the host's main/tick tags when updating a single song.

## 8. Pitfalls of a pure PowerShell 5.1 environment with no Python

- Variable names are **case-insensitive**: a parser local variable `$tag` overwrites the generation config `$TAG` (measured, it bit us);
- No ternary `?:`, no `??`; in command mode `ReadStr 4 -ne "MTrk"` treats `-ne` as an argument — assign to a variable first, then compare;
- A .ps1 containing non-ASCII must have a **UTF-8 BOM**, otherwise Chinese paths/strings are misread as GBK;
- When called from bash, backtick escaping is eaten by bash first; writing a .ps1 file and running it with `-File` is the most reliable;
- Regression-test the varlen/pairing logic on a small known-good file (e.g. the MIDI corresponding to the lemon reference pack) before running it on the real file.

## 9. The consistency self-check that must be done before delivery (the generation back end, not MIDI parsing)

An **intermittent silent-note bug** found in a real delivery; check for it on every order:

- If `generate.py`'s tree leaf is written 2 blocks wide (`b-a<=1`) but only outputs `rng[0]`, then when "an adjacent tick pair `(2k,2k+1)`
  both has notes", `notes/2k+1.mcfunction` is generated but **no tree node calls it** → that note is permanently silent.
  The deepest leaf produced by bisection is always the aligned `[2k,2k+1]`, so an adjacent pair whose lower tick is odd, `(2k+1,2k+2)`, belongs to two
  different leaves and is unaffected — only half of the adjacent pairs are eaten, which is extremely hard to notice by ear.
- Measured: of 1169 notes in one song, **79 are unreachable**; upstream finished packs after_the_rain 491, fanwutuobang 85;
  while badapple's 639 adjacent tick pairs all happen to have odd lower ticks and escape with 0 losses — which is exactly why it went undetected for so long.
- The same 2-block-wide leaf has a second side effect: **notes in its right half fire 1 game tick (50 ms) early**. The window is counted from the leaf's left
  boundary 80a, so notes with t=2k+1 are hit when nbs_s = 80·2k. Measured on the upstream example pack fanwutuobang_demo:
  **54 of its 117 notes fire 1 tick early** (e.g. the leaf of notes/3 is `2_3`, window `160..400`, so it sounds at game tick 2).
  A 1-block-wide leaf's window `80t..80t+160` triggers exactly at game tick = t, and both problems disappear together.
- Self-check criteria (failing any one counts as failure):
  1. Every `notes/<t>.mcfunction` is **referenced exactly once** by the tree;
  2. Every tree node is **reachable** from the tree root in tick.mcfunction, with no dangling child nodes;
  3. Run the tree state-machine simulation (`nbs_s += #speed` → descend level by level by window/guard → record the notes actually called),
     and assert that every note tick triggers exactly once at **game tick == t** (this catches silent notes as well as early firing/duplicates).
- Just run `python3 scripts/validate_pack.py --pack <datapack root> --namespace <ns> --song <song name> --song-id <id> --speed <value>`,
  which checks the three items above together with the instrument whitelist, pitch range, CRLF and tags.

> Conclusion: **leaf width = 1 block** is a hard requirement (see `references/format_spec.md` §A); the window/guard formulas do not need to change.
