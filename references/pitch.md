# Pitch conversion
- use-count n ∈ [0,24]; /playsound pitch = 2^((n-12)/12); n=12 → 1.0 (F#4)
- MC measured clamp: pitch < 0.5 counts as 0.5, > 2.0 counts as 2.0 — anything outside must be shifted an octave, you cannot rely on the clamp
- Note conversion: use-count = MIDI − instrument base (the base column in instruments.md)
- Combined effective pitch range F#1–F#7 (72 semitones): low 2 octaves bass/didgeridoo; low 1 octave guitar/trumpet_weathered/oxidized;
  standard harp/pling/bit/banjo/iron_xylophone/cow_bell/trumpet/trumpet_exposed; high 1 octave flute; high 2 octaves bell/chime/xylophone

| n | Note name | pitch | | n | Note name | pitch |
|---|---|---|---|---|---|---|
| 0 | F#3 | 0.5 | | 12 | F#4 | 1.0 |
| 1 | G3 | 0.529732 | | 13 | G4 | 1.059463 |
| 2 | G#3 | 0.561231 | | 14 | G#4 | 1.122462 |
| 3 | A3 | 0.594604 | | 15 | A4 | 1.189207 |
| 4 | A#3 | 0.629961 | | 16 | A#4 | 1.259921 |
| 5 | B3 | 0.667420 | | 17 | B4 | 1.334840 |
| 6 | C4 | 0.707107 | | 18 | C5 | 1.414214 |
| 7 | C#4 | 0.749154 | | 19 | C#5 | 1.498307 |
| 8 | D4 | 0.793701 | | 20 | D5 | 1.587401 |
| 9 | D#4 | 0.840896 | | 21 | D#5 | 1.681793 |
| 10 | E4 | 0.890899 | | 22 | E5 | 1.781797 |
| 11 | F4 | 0.943874 | | 23 | F5 | 1.887749 |
| — | — | — | | 24 | F#5 | 2.0 |
