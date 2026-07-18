#!/usr/bin/env python3
"""Wait for auto_punctuate PID, convert outputs to simplified, verify, keep in active corpus."""
import os, re, sys, time
from pathlib import Path
from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 3418750
LOG = ROOT / "logs" / "auto_punctuate.log"
ACTIVE = ROOT / "data" / "先秦"
NAMES = ['七国考.txt', '路史.txt', '绎史.txt']
cc = OpenCC('t2s')

def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

print(f'watching pid={PID}', flush=True)
while alive(PID):
    if LOG.exists():
        lines = [l for l in LOG.read_text(errors='replace').splitlines() if any(n in l for n in NAMES)]
        if lines:
            print('latest:', lines[-1], flush=True)
    time.sleep(30)

print('process ended, post-processing...', flush=True)
for name in NAMES:
    p = ACTIVE / name
    if not p.exists():
        print('MISSING', name, flush=True)
        continue
    t = p.read_text(encoding='utf-8', errors='replace')
    s = cc.convert(t)
    if s != t:
        p.write_text(s, encoding='utf-8')
        t = s
        print(f't2s {name}', flush=True)
    punct = len(re.findall(r'[，。！？；：、]', t))
    periods = t.count('。')
    print(f'OK {name}: chars={len(t)} punct={punct} 。={periods}', flush=True)
    if periods < 50:
        print(f'WARN low punctuation: {name}', flush=True)

print('DONE ingest ready in data/先秦/', flush=True)
