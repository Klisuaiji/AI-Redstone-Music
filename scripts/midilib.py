#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MIDI reader library (shared by scan_midi.py / midi_to_song.py).

Implemented from the field-tested lessons in references/midi_notes.md:
  - **Count note-on only** (0x90 vel>0), never relying on note-on/off pairing -- a pairing parser
    overwrites overlapping notes of the same pitch, badly undercounting notes and producing
    "stuck notes"; a note block only needs onsets, duration is useless.
  - **Do not trust the header's format field**; parse by chunk order instead (format 0 with
    several MTrk chunks is illegal but does occur in the wild).
  - **Route parts by track name (FF 03)**, not by index -- deleting one track shifts every index,
    but the names stay the same.
  - varlen continuation byte has the top bit set; running status reuses the previous status byte
    and is cleared after F0/F7.

Standard library only. Produces no output when imported.
"""
import struct

__all__ = ["Note", "Track", "Midi", "read_midi", "gm_drum_name", "GM_DRUMS"]

# GM percussion pitch -> name (used by the scan_midi report and midi_to_song's drum mapping notes)
GM_DRUMS = {
    35: "acoustic bass drum", 36: "bass drum", 37: "side stick",
    38: "snare", 39: "hand clap", 40: "electric snare",
    41: "low tom", 42: "closed hi-hat", 43: "high tom", 44: "pedal hi-hat",
    45: "mid tom", 46: "open hi-hat", 47: "low-mid tom", 48: "high-mid tom",
    49: "crash cymbal", 50: "high tom", 51: "ride cymbal", 52: "china cymbal",
    53: "ride bell", 54: "tambourine", 55: "splash cymbal", 56: "cowbell",
    57: "crash cymbal 2", 58: "vibraslap", 59: "ride cymbal 2", 60: "hi bongo",
    61: "low bongo", 62: "hi conga", 63: "low conga", 64: "high timbale",
}


def gm_drum_name(pitch):
    return GM_DRUMS.get(pitch, "percussion %d" % pitch)


class Note(object):
    """One note-on. tick = MIDI tick; vel = velocity (1-127)."""

    __slots__ = ("tick", "pitch", "vel", "chan")

    def __init__(self, tick, pitch, vel, chan):
        self.tick = tick
        self.pitch = pitch
        self.vel = vel
        self.chan = chan

    def __repr__(self):
        return "Note(t=%d,p=%d,v=%d,ch=%d)" % (self.tick, self.pitch, self.vel, self.chan)


class Track(object):
    def __init__(self, index, name):
        self.index = index
        self.name = name or "(unnamed)"
        self.notes = []          # [Note]
        self.programs = []       # [(tick, program)]
        self.channels = set()
        self.control = []        # [(tick, cc, value)]

    @property
    def is_drum(self):
        return 9 in self.channels

    def pitches(self):
        return sorted(set(n.pitch for n in self.notes))

    def __repr__(self):
        return "Track(%d,%r,notes=%d)" % (self.index, self.name, len(self.notes))


class Midi(object):
    def __init__(self, path):
        self.path = path
        self.fmt = 1
        self.declared_ntrks = 0
        self.division = 480
        self.tracks = []
        self.tempos = [(0, 500000)]      # [(tick, us_per_quarter)]

    # ---------- time conversion ----------
    def us_at(self, tick):
        us = self.tempos[0][1]
        for tk, u in self.tempos:
            if tk > tick:
                break
            us = u
        return us

    def bpm_at(self, tick=0):
        return 60e6 / self.us_at(tick)

    def sec_at(self, tick):
        """tick -> seconds (piecewise integration over the tempo map)."""
        s = 0.0
        last = 0
        us = self.tempos[0][1]
        for tk, u in self.tempos:
            if tk >= tick:
                break
            s += (tk - last) / float(self.division) * (us / 1e6)
            last, us = tk, u
        s += (tick - last) / float(self.division) * (us / 1e6)
        return s

    def ticks_per_second(self, tick=0):
        return self.division * 1e6 / self.us_at(tick)

    def last_note_tick(self):
        return max([n.tick for t in self.tracks for n in t.notes] or [0])

    @property
    def note_count(self):
        return sum(len(t.notes) for t in self.tracks)


def _read_varlen(b, i):
    v = 0
    while True:
        c = b[i]
        i += 1
        v = (v << 7) | (c & 0x7F)
        if not (c & 0x80):
            return v, i


def read_midi(path):
    """Parse a MIDI file and return a Midi object. Tolerates illegal but common structures."""
    b = open(path, "rb").read()
    if b[:4] != b"MThd":
        raise ValueError("not a MIDI file (missing MThd): %s" % path)
    hlen = struct.unpack(">I", b[4:8])[0]
    m = Midi(path)
    m.fmt = struct.unpack(">H", b[8:10])[0]
    m.declared_ntrks = struct.unpack(">H", b[10:12])[0]
    div = struct.unpack(">H", b[12:14])[0]
    if div & 0x8000:
        raise ValueError("SMPTE time division (division=0x%04x) is not supported yet; re-save as PPQ in your DAW" % div)
    m.division = div or 480

    pos = 8 + hlen
    idx = 0
    while pos + 8 <= len(b):
        cid = b[pos:pos + 4]
        clen = struct.unpack(">I", b[pos + 4:pos + 8])[0]
        data = b[pos + 8:pos + 8 + clen]
        pos += 8 + clen
        if cid != b"MTrk":
            continue
        tr = Track(idx, None)
        idx += 1
        i = 0
        tick = 0
        status = None
        while i < len(data):
            dt, i = _read_varlen(data, i)
            tick += dt
            if i >= len(data):
                break
            c = data[i]
            if c & 0x80:
                status = c
                i += 1
            if status is None:
                break
            if status == 0xFF:
                if i >= len(data):
                    break
                mt = data[i]
                i += 1
                ln, i = _read_varlen(data, i)
                payload = data[i:i + ln]
                i += ln
                if mt == 0x03:
                    tr.name = payload.decode("utf-8", "replace").strip("\x00").strip()
                elif mt == 0x51 and ln == 3:
                    m.tempos.append((tick, struct.unpack(">I", b"\x00" + payload)[0]))
            elif status in (0xF0, 0xF7):
                ln, i = _read_varlen(data, i)
                i += ln
                status = None                      # running status is cleared after SysEx
            else:
                hi = status & 0xF0
                ch = status & 0x0F
                n = 1 if hi in (0xC0, 0xD0) else 2
                d = data[i:i + n]
                i += n
                if len(d) < n:
                    break
                if hi == 0x90 and d[1] > 0:        # accept note-on only
                    tr.notes.append(Note(tick, d[0], d[1], ch))
                    tr.channels.add(ch)
                elif hi == 0x80:
                    tr.channels.add(ch)
                elif hi == 0xC0:
                    tr.programs.append((tick, d[0]))
                elif hi == 0xB0:
                    tr.control.append((tick, d[0], d[1]))
        m.tracks.append(tr)

    # dedupe and sort the tempo map
    seen = set()
    tmap = []
    for tk, u in sorted(m.tempos):
        if tk in seen:
            continue
        seen.add(tk)
        tmap.append((tk, u))
    m.tempos = tmap or [(0, 500000)]
    return m
