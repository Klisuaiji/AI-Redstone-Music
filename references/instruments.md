# Note block instrument whitelist (source: Minecraft Wiki "Note Block", verified)

## Java 1.13+ (datapack starting point, 10 total)
| Instrument ID | Name | Sound event | Block underneath | Pitch range base (use-count 0=F#) |
|---|---|---|---|---|
| harp | harp (piano) | block.note_block.harp | any/air | F#3 (MIDI 54) |
| bass | bass guitar | block.note_block.bass | wood-type | F#1 (MIDI 30) |
| basedrum | kick drum | block.note_block.basedrum | stone-type | — |
| snare | snare drum | block.note_block.snare | sand/gravel | — |
| hat | hi-hat | block.note_block.hat | glass-type | — |
| bell | bell (glockenspiel) | block.note_block.bell | gold block | F#5 (MIDI 78) |
| flute | flute | block.note_block.flute | clay block | F#4 (MIDI 66) |
| chime | wind chime | block.note_block.chime | packed ice | F#5 (MIDI 78) |
| guitar | guitar | block.note_block.guitar | wool/slab/stairs | F#2 (MIDI 42) |
| xylophone | xylophone | block.note_block.xylophone | bone block | F#5 (MIDI 78) |

## Added in 1.14+ (19w09a, 6 more → 16 total)
| iron_xylophone | iron xylophone (vibraphone) | block.note_block.iron_xylophone | iron block | F#3 (54) |
| cow_bell | cow bell | block.note_block.cow_bell | soul sand | F#3 (54) |
| didgeridoo | didgeridoo | block.note_block.didgeridoo | pumpkin | F#1 (30) |
| bit | bit (clarinet/synth) | block.note_block.bit | emerald block | F#3 (54) |
| banjo | banjo | block.note_block.banjo | hay bale | F#3 (54) |
| pling | electric piano | block.note_block.pling | glowstone | F#3 (54) |

## 1.20+ (experimental in 1.19.3/1.19.4; ⚠ ignores pitch, percussive/sound-effect only)
skeleton→block.note_block.imitate.skeleton;wither_skeleton→.imitate.wither_skeleton;
zombie→.imitate.zombie;creeper→.imitate.creeper;piglin→.imitate.piglin;dragon→.imitate.ender_dragon

## 26.1+ (copper block note blocks)
trumpet→block.note_block.trumpet (F#3,54);trumpet_exposed→.trumpet_exposed (54);
trumpet_weathered→.trumpet_weathered (F#2,42);trumpet_oxidized→.trumpet_oxidized (42)

## NBS project instrument index → MC instrument
0 harp, 1 bass, 2 basedrum, 3 snare, 4 hat, 5 guitar, 6 flute, 7 bell, 8 chime,
9 xylophone, 10 iron_xylophone, 11 cow_bell, 12 didgeridoo, 13 bit, 14 banjo, 15 pling
(custom instruments: take their sound_name, map it if it is in the whitelist above, otherwise skip and warn)
