#!/usr/bin/env python3
# .nbs (Open Note Block Studio) → song.json; classic format first, with auto-detection of the new OpenNBS format
import struct, json, sys, argparse

NBS2MC = ["harp","bass","basedrum","snare","hat","guitar","flute","bell","chime",
          "xylophone","iron_xylophone","cow_bell","didgeridoo","bit","banjo","pling"]

class R:
    def __init__(s, b): s.b=b; s.i=0
    def u8(s):  v=s.b[s.i]; s.i+=1; return v
    def i16(s): v=struct.unpack(">h",s.b[s.i:s.i+2])[0]; s.i+=2; return v
    def i32(s): v=struct.unpack(">i",s.b[s.i:s.i+4])[0]; s.i+=4; return v
    def s16(s): v=struct.unpack(">H",s.b[s.i:s.i+2])[0]; s.i+=2; return v
    def s32(s): v=struct.unpack(">I",s.b[s.i:s.i+4])[0]; s.i+=4; return v
    def s(s):
        n=s.s32(); v=s.b[s.i:s.i+n].decode("utf-8","replace"); s.i+=n; return v

def parse(path):
    r = R(open(path,"rb").read())
    ver = 0
    if r.i16() == 0:            # new OpenNBS format: 0 signature + version + default instrument count
        ver = r.u8(); r.u8(); length=r.s16(); layers=r.s16()
    else:                       # classic format: the first short is the length
        r.i = 0; length=r.s16(); layers=r.s16()
    r.s(); r.s(); r.s(); r.s()  # name/author/origin author/description
    tps = r.i16()/100.0
    r.u8(); r.u8(); r.u8()
    r.i32(); r.i32(); r.i32(); r.i32(); r.i32()
    if ver == 0: r.s()          # classic format trailing file name
    else:
        # new format v1+: loop/loopcount/loopstart; v2+: midi name. Best-effort read in spec order
        try:
            if ver >= 1: r.u8(); r.u8(); r.s16()
            if ver >= 2: r.s()
        except Exception: pass
    notes = {}   # layer -> [(tick, inst, key, vel)]
    tick = 0
    while True:
        jump = r.s16()
        if jump == 0: break
        tick += jump
        while True:
            lj = r.u8()
            if lj == 0: break
            layer = (layer + lj) if 'layer' in dir() else lj
            inst = r.u8(); key = r.u8()
            vel, pan, pit = 100, 0, key*100
            if ver >= 2: vel = r.u8(); pan = r.u8(); pit = r.s16()
            notes.setdefault(layer, []).append((tick, inst, key, vel))
    tracks = []
    for layer in sorted(notes):
        tn = []
        for (tick, inst, key, vel) in sorted(notes[layer]):
            mc = NBS2MC[inst] if inst < len(NBS2MC) else None
            if mc is None: continue
            tn.append({"t": tick, "midi": key + 21, "inst": mc, "vol": max(1, vel)/100.0})
        if tn:
            tracks.append({"name": "layer_%d" % layer, "include": True,
                           "instrument_default": tn[0]["inst"], "notes": tn})
    return tps, tracks

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("nbs"); ap.add_argument("-o","--out",required=True)
    ap.add_argument("--meta", default="{}", help='JSON string, e.g. {"mc_version":"1.20.4","song_id":9}')
    a = ap.parse_args()
    tps, tracks = parse(a.nbs)
    meta = {"name":"song","namespace":"minecraft","path":"music/song","mc_version":"1.21",
            "style":"lemon","time_unit":"nbs_ticks","tempo_tps":tps,"speed":2,
            "auto_stop":True,"next_song":None,"mute_tag":"no_music"}
    meta.update(json.loads(a.meta))
    meta["path"] = "music/" + meta["name"]
    json.dump({"meta":meta,"tracks":tracks}, open(a.out,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print("OK: %d tracks, tps=%s → %s (midi=key+21 is the note block notation)" % (len(tracks), tps, a.out))

if __name__ == "__main__": main()
