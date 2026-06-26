from __future__ import annotations

import csv
from pathlib import Path

from .adapters.nsec3map import parse_nsec3_chain_rows
from .adapters.potfile import normalize_nsec3_discovered_name

NSEC3_CHAIN_HEADER = [
    'index', 'status', 'hash', 'next_hash', 'plaintext', 'fqdn',
    'algorithm', 'flags', 'iterations', 'salt', 'rrtypes',
]


def parse_potfile_cracks(path):
    cracks = {}
    p = Path(path)
    if not p.exists():
        return cracks
    with p.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            text = line.rstrip('\r\n')
            if not text.strip() or ':' not in text:
                continue
            hash_side, plaintext = text.rsplit(':', 1)
            cracks[hash_side] = plaintext
            owner_hash = hash_side.split(':', 1)[0]
            cracks.setdefault(owner_hash, plaintext)
    return cracks


def write_nsec3_chain_report(workspace_root, zone):
    root = Path(workspace_root)
    rows = parse_nsec3_chain_rows(root / 'nsec3map/zone.txt', zone)
    if not rows:
        return None
    cracks = parse_potfile_cracks(root / 'scheduler/run.pot')
    reports = root / 'reports'
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / 'nsec3_chain.tsv'
    with out.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t', lineterminator='\n')
        writer.writerow(NSEC3_CHAIN_HEADER)
        for index, row in enumerate(rows):
            owner_hash = row.get('hash', '')
            cracked = owner_hash in cracks
            plaintext = cracks[owner_hash] if cracked else ''
            fqdn = normalize_nsec3_discovered_name(plaintext, zone) if cracked else ''
            writer.writerow([
                index,
                'cracked' if cracked else 'uncracked',
                owner_hash,
                row.get('next_hash', '') or '',
                plaintext,
                fqdn or '',
                row.get('algorithm', '') or '',
                row.get('flags', '') or '',
                row.get('iterations', '') or '',
                row.get('salt', '') or '',
                row.get('rrtypes', '') or '',
            ])
    return out
