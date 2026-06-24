from pathlib import Path


def display_name_from_potfile_plaintext(plaintext):
    if str(plaintext).strip() == '':
        return '@'
    return str(plaintext).strip().lower().rstrip('.')


def normalize_nsec3_discovered_name(value: str, zone: str) -> str | None:
    zone = str(zone or '').strip().rstrip('.').lower()
    value = str(value or '').strip().rstrip('.').lower()
    if not zone:
        return None
    if value == '' or value == '@':
        return zone
    if value == zone:
        return zone
    if value.endswith('.' + zone):
        return value
    return f"{value}.{zone}"


def normalize_discovered_names(names, source='nsec3', zone=''):
    out = []
    seen = set()
    for name in names or []:
        if source == 'nsec3':
            normalized = normalize_nsec3_discovered_name(name, zone)
        else:
            normalized = str(name or '').strip().lower().rstrip('.')
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


class PotfileTail:
    def __init__(self,path):
        self.path=Path(path); self.offset=0; self.seen=set(); self.cracked_hashes_seen=set(); self.cracked_count=0
    def poll(self):
        if not self.path.exists(): return []
        with self.path.open('r',errors='ignore') as f:
            f.seek(self.offset); lines=f.readlines(); self.offset=f.tell()
        out=[]
        for line in lines:
            line=line.rstrip('\r\n')
            if not line.strip() or line in self.seen or ':' not in line: continue
            self.seen.add(line); hash_part, plaintext = line.rsplit(':', 1)
            if hash_part not in self.cracked_hashes_seen:
                self.cracked_hashes_seen.add(hash_part); self.cracked_count=len(self.cracked_hashes_seen)
            cand=display_name_from_potfile_plaintext(plaintext)
            if cand not in out: out.append(cand)
        return out


def extract_potfile_names(path, zone=None):
    p = Path(path)
    names = []
    malformed = 0
    if not p.exists():
        return names, malformed
    seen = set()
    with p.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            text = line.rstrip('\r\n')
            if not text.strip():
                continue
            if ':' not in text:
                malformed += 1
                continue
            _hash_part, plaintext = text.rsplit(':', 1)
            name = display_name_from_potfile_plaintext(plaintext)
            if zone is not None:
                name = normalize_nsec3_discovered_name(name, zone)
            if name and name not in seen:
                seen.add(name); names.append(name)
    return names, malformed
