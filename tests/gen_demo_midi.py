#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 examples/demo.mid —— 8 小节 C 大调示例（120 BPM，主旋律+贝斯+鼓）。

刻意包含两个"该被工具处理好"的细节：
  * 第 4 小节有一个同 onset 的两音和弦（F4+A4）—— 去重只能按 (tick,乐器,音高)，不能吞掉和弦
  * 第 4 小节军鼓有一个 48 MIDI tick 的 flam（= 1 个游戏 tick）—— 会产生相邻音符 tick，
    正好踩在上游"2 格宽叶子吃掉第二个音符"的坑上，所以它也是 tests/smoke_test.py 的回归素材

    python3 tests/gen_demo_midi.py examples/demo.mid
仅用标准库。
"""
import os, struct, sys

PPQ = 480
BPM = 120
Q = PPQ                      # 一个四分音符的 tick 数


def varlen(n):
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def track(events, name):
    ev = [(0, b"\xff\x03" + varlen(len(name)) + name.encode("utf-8"))]
    ev += events
    ev.sort(key=lambda e: e[0])
    data = bytearray()
    last = 0
    for tick, payload in ev:
        data += varlen(tick - last) + payload
        last = tick
    data += varlen(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "examples/demo.mid"

    def on(tick, ch, pitch, vel=96):
        return (tick, bytes([0x90 | ch, pitch, vel]))

    def off(tick, ch, pitch):
        return (tick, bytes([0x80 | ch, pitch, 0]))

    # ---- 主旋律（C 大调，8 小节；含一个同 onset 和弦）----
    mel = [(0, 60), (0.5, 62), (1, 64), (1.5, 65), (2, 67), (3, 67),
           (4, 69), (4.5, 67), (5, 65), (5.5, 64), (6, 62), (7, 60),
           (8, 64), (8.5, 64), (9, 67), (9.5, 67), (10, 72), (11, 71),
           (12, 69), (12.5, 67), (13, 65), (13.5, 64), (14, 62), (14.5, 64),
           (15, 65), (15, 69),                       # ← 同 tick 两音和弦 F4+A4
           (16, 72), (17, 71), (18, 69), (19, 67),
           (20, 65), (21, 64), (22, 62), (23, 60),
           (24, 60), (24.5, 64), (25, 67), (25.5, 72), (26, 71), (27, 69),
           (28, 67), (29, 65), (30, 60), (31, 60)]
    me = []
    for q, p in mel:
        me += [on(int(q * Q), 0, p), off(int(q * Q) + int(0.45 * Q), 0, p)]
    # ---- 贝斯：每小节根音 ----
    bass = [(0, 36), (4, 36), (8, 41), (12, 41), (16, 43), (20, 43), (24, 36), (28, 36)]
    be = []
    for q, p in bass:
        be += [on(int(q * Q), 1, p, 100), off(int(q * Q) + int(3.8 * Q), 1, p)]
    # ---- 鼓：底鼓 1/3 拍、军鼓 2/4 拍、踩镲八分；第 4 小节军鼓带 1 游戏 tick 的 flam ----
    de = []
    for bar in range(8):
        b = bar * 4 * Q
        for beat in (0, 2):
            de += [on(b + beat * Q, 9, 36, 110), off(b + beat * Q + 30, 9, 36)]
        for beat in (1, 3):
            de += [on(b + beat * Q, 9, 38, 100), off(b + beat * Q + 30, 9, 38)]
        for i in range(8):
            de += [on(b + i * Q // 2, 9, 42, 70), off(b + i * Q // 2 + 20, 9, 42)]
    flam = 13 * Q                                  # 13 拍 + 48 tick(=1 游戏 tick) 的连击
    de += [on(flam, 9, 38, 100), off(flam + 20, 9, 38),
           on(flam + 48, 9, 38, 90), off(flam + 48 + 20, 9, 38)]

    # ---- 组装 ----
    cond = [(0, b"\xff\x51\x03" + struct.pack(">I", int(60e6 / BPM))[1:]),
            (0, b"\xff\x58\x04\x04\x02\x18\x08")]      # 4/4 拍号
    data = (track(cond, "conductor") + track(me, "piano lead") +
            track(be, "electric bass") + track(de, "drums"))
    header = b"MThd" + struct.pack(">IHHH", 6, 1, 4, PPQ)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(header + data)
    print("%s  %d 字节  %d BPM  8 小节  旋律 %d 音 / 贝斯 %d 音 / 鼓 %d 次"
          % (out, os.path.getsize(out), BPM, len(mel), len(bass), len(de) // 2))


if __name__ == "__main__":
    main()
