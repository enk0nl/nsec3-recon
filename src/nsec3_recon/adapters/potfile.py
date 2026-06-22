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
