#!/usr/bin/env python3
import argparse
from collections import Counter
from pathlib import Path

def norm(s):
    s=s.strip().lower().rstrip('.')
    return s or None

def combine(inputs):
    c=Counter()
    for p in inputs:
        with open(p, errors='ignore') as f:
            for line in f:
                n=norm(line)
                if n: c[n]+=1
    return [k for k,_ in sorted(c.items(), key=lambda kv:(-kv[1], kv[0]))]

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--output', required=True); ap.add_argument('inputs', nargs='+')
    a=ap.parse_args(argv); out=Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(combine(a.inputs))+'\n')
if __name__=='__main__': main()
