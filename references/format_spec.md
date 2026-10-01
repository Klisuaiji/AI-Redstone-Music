# lemon datapack specification (reverse-verified) and the song.json contract

## A. Specification of the generated artifacts (file-by-file comparison with the reference pack lemon)
Scoring conventions: fake player `music_progress`; objectives `music_type` (current song ID)/`nbs_s` (progress)/`nbs_t` (ticks already played);
each tick `#speed nbs_s` is added to nbs_s. All times are in nbs_s units (= NBS tick × 20/tps × speed).

- play.mcfunction: `music_type=<id>`; `nbs_s=0`; `nbs_t=-1`
- stop.mcfunction: `nbs_s=0`; `reset nbs_t`; optional `function <next>` (next-song chain)
- tick.mcfunction: two lines, first `+= #speed nbs_s` then call the tree root, both carrying `if music_type matches <id>`
- notes/<t>.mcfunction (CRLF line endings):
  `execute as @a[tag=!no_music] at @s run playsound minecraft:<event> voice @s ^0 ^ ^ <vol> <pitch6digits> 1` ×N
  last line `scoreboard players set music_progress nbs_t <t>`; if t is the last tick of the whole song: do not write nbs_t, use `function <ns>:<path>/stop` instead
- tree/<a>_<b>.mcfunction: covers [0, N-1], N=2^⌈log2(max+1)⌉
  - prune empty ranges; **b−a == 0 and contains notes → leaf (must be 1 block wide)**: `matches 80a..(80a+160)` + `nbs_t matches ..<t-1>` (..-1 when t=0) → notes/<t>
  - ⚠ Writing the leaf 2 blocks wide (b−a≤1) makes it permanently silent: the leaf only outputs one note, `rng[0]`, while the deepest leaf produced by
    bisecting [0,N-1] is always the aligned `[2k,2k+1]`, so when "an adjacent tick pair (2k,2k+1) both have notes", the notes file for
    2k+1 is generated but no node ever calls it. Measured on one song: 79 of 1169 notes are unreachable (upstream RedstoneMusicBox-v3's
    after_the_rain has 491, fanwutuobang has 85); the adjacent pair (2k+1,2k+2) belongs to two different leaves and is unaffected,
    so this is an intermittent bug that is very hard to notice by ear. After switching to 1 block wide the window/guard formulas are completely unchanged; only the tree depth grows by 1 (node count roughly ×1.4).
  - ⚠ A 2-block-wide leaf also makes notes **fire 1 game tick (50 ms) early**: the window is counted from the leaf's left boundary 80a, so notes falling in the
    right half of the leaf (t=2k+1) are hit by the window and triggered at nbs_s = 80·2k. Measured on the upstream example pack fanwutuobang_demo:
    **54 of its 117 notes fire 1 tick early** (e.g. the leaf of notes/3 is `2_3`, window `160..400`, so it sounds at game tick 2);
    a 1-block-wide leaf's window is `80t..80t+160`, triggering exactly at game tick = t.
  - otherwise m=(a+b)//2; left child window `80a..80(m+3)`, right child `80(m+1)..80(b+4)` (internal nodes have no nbs_t guard)
  - a single-child node outputs its corresponding window line as usual

## B. song.json Schema
{
  "meta": {
    "name": "lemon",                 // song name (lowercase English, used for the path)
    "namespace": "minecraft",        // datapack namespace
    "path": "music/lemon",           // function path = namespace:path/...
    "song_id": 8,                    // required in lemon-compatible mode, for duplicate checking
    "mc_version": "1.20.4",          // validates the instrument whitelist
    "style": "lemon",                // lemon | standalone
    "time_unit": "nbs_ticks",        // nbs_ticks | game_ticks | nbs_s_units
    "tempo_tps": 10,                 // NBS ticks per second (the common derivation from BPM120/quarter note 0.5s → tps=2×2=10: tps=BPM/6)
    "speed": 2,                      // datapack #speed; nbs_ticks conversion scale=20/tps*speed
    "auto_stop": true,               // automatically chain to stop on the last tick
    "next_song": "minecraft:music/baka/play",  // may be null
    "mute_tag": "no_music"
  },
  "tracks": [
    { "name": "vocal_melody", "include": true, "instrument_default": "harp",
      "notes": [ {"t": 0, "midi": 66, "inst": "harp", "vol": 1.0}, ... ] }
  ]
}
Fields: t = note start (in time_unit units, must make t×scale an integer); midi = pitch (0-127); inst may be omitted to use the default; vol∈(0,1].
1 track holds 1 part; give the vocal melody its own track so it can be stripped on user request.

## C. nbs_to_json.py output notes
Parses .nbs (classic format first, auto-detecting the new OpenNBS format): splits tracks by layer, t = raw NBS tick,
tempo_tps = header tempo/100, midi = key+33 (NBS key 0-87 ↔ F#1-F#7; this tool stores key+21 directly to align with note block
MIDI notation and marks "key_offset":21 in meta for generate to compensate — the actual implementation follows the script source comments).
On parse failure: ask the user to save-as/export text in OpenNBS, or switch to MIDI.

## D. Manual generation (no code environment) memo
Leaf window constant: 80 is the tick scale (= 4 units × 20? No — the generator always follows the formula in the previous section, do not derive it yourself);
**leaf width must be 1 block** (see the silent-note warning in §A);
pitch is uniformly 6 decimal places; every line is CRLF; the tree file name is the range itself, "a_b".
Before delivery run `python3 scripts/validate_pack.py --pack <datapack root> ...` as a self-check (includes the tree state-machine simulation).
