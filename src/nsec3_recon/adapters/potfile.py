from pathlib import Path
class PotfileTail:
    def __init__(self,path): self.path=Path(path); self.offset=0; self.seen=set()
    def poll(self):
        if not self.path.exists(): return []
        with self.path.open('r',errors='ignore') as f:
            f.seek(self.offset); lines=f.readlines(); self.offset=f.tell()
        out=[]
        for line in lines:
            line=line.strip()
            if not line or line in self.seen: continue
            self.seen.add(line); cand=line.rsplit(':',1)[-1]
            if cand not in out: out.append(cand)
        return out


def extract_potfile_names(path):
    p = Path(path)
    names = []
    malformed = 0
    if not p.exists():
        return names, malformed
    seen = set()
    with p.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            if ':' not in text:
                malformed += 1
                continue
            name = text.rsplit(':', 1)[-1].strip().lower().rstrip('.')
            if name and name not in seen:
                seen.add(name); names.append(name)
    return names, malformed
