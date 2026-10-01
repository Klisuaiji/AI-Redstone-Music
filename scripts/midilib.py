#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MIDI 读取库（scan_midi.py / midi_to_song.py 共用）。

按 references/midi_notes.md 的实战经验实现：
  - **只数 note-on**（0x90 vel>0），不依赖 note-on/off 配对 —— 配对式解析器遇到同音高重叠会互相覆盖，
    音符数大幅少计并产生"粘住音符"；音符盒只要 onset，时长无用。
  - **不信任 header 的 format 字段**，按 chunk 顺序解析（format 0 带多个 MTrk 是非法但真实存在的）。
  - **按轨道名（FF 03）路由声部**，不按下标 —— 删一条轨后下标全变，名字不变。
  - varlen 续字节最高位 = 1；running status 沿用上一个状态字节，F0/F7 之后清零。

仅用标准库。被 import 时不产生输出。
"""
import struct

__all__ = ["Note", "Track", "Midi", "read_midi", "gm_drum_name", "GM_DRUMS"]

# GM 打击乐音高 → 名称（用于 scan_midi 报告与 midi_to_song 的鼓映射说明）
GM_DRUMS = {
    35: "底鼓(acoustic bass drum)", 36: "底鼓", 37: "边击(side stick)",
    38: "军鼓", 39: "拍手(hand clap)", 40: "军鼓(electric snare)",
    41: "低音桶鼓", 42: "闭合踩镲", 43: "高音桶鼓", 44: "踏板踩镲",
    45: "中音桶鼓", 46: "开放踩镲", 47: "中低桶鼓", 48: "中高桶鼓",
    49: "叮镲(crash)", 50: "高音桶鼓", 51: "叮点镲(ride)", 52: "中国镲",
    53: "铃铛(ride bell)", 54: "铃鼓", 55: "飞溅镲", 56: "牛铃",
    57: "叮镲2(crash2)", 58: "振动铃", 59: "叮点镲2(ride2)", 60: "高音邦戈",
    61: "低音邦戈", 62: "高音康加", 63: "低音康加", 64: "高音定音鼓",
}


def gm_drum_name(pitch):
    return GM_DRUMS.get(pitch, "打击乐 %d" % pitch)


class Note(object):
    """一个 note-on。tick = MIDI tick；vel = 力度(1-127)。"""

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

    # ---------- 时间换算 ----------
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
        """tick → 秒（按 tempo map 分段积分）。"""
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
    """解析 MIDI 文件，返回 Midi 对象。非法但常见的结构也尽量容错。"""
    b = open(path, "rb").read()
    if b[:4] != b"MThd":
        raise ValueError("不是 MIDI 文件（缺少 MThd）：%s" % path)
    hlen = struct.unpack(">I", b[4:8])[0]
    m = Midi(path)
    m.fmt = struct.unpack(">H", b[8:10])[0]
    m.declared_ntrks = struct.unpack(">H", b[10:12])[0]
    div = struct.unpack(">H", b[12:14])[0]
    if div & 0x8000:
        raise ValueError("SMPTE 时间制式（division=0x%04x）暂不支持，请在 DAW 里另存为 PPQ 制式" % div)
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
                status = None                      # SysEx 之后 running status 清零
            else:
                hi = status & 0xF0
                ch = status & 0x0F
                n = 1 if hi in (0xC0, 0xD0) else 2
                d = data[i:i + n]
                i += n
                if len(d) < n:
                    break
                if hi == 0x90 and d[1] > 0:        # 只认 note-on
                    tr.notes.append(Note(tick, d[0], d[1], ch))
                    tr.channels.add(ch)
                elif hi == 0x80:
                    tr.channels.add(ch)
                elif hi == 0xC0:
                    tr.programs.append((tick, d[0]))
                elif hi == 0xB0:
                    tr.control.append((tick, d[0], d[1]))
        m.tracks.append(tr)

    # tempo map 去重排序
    seen = set()
    tmap = []
    for tk, u in sorted(m.tempos):
        if tk in seen:
            continue
        seen.add(tk)
        tmap.append((tk, u))
    m.tempos = tmap or [(0, 500000)]
    return m
