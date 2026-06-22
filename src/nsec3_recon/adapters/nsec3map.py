from pathlib import Path

def classify_zone_file(path):
    text=Path(path).read_text(encoding='utf-8', errors='ignore').upper() if Path(path).exists() else ''
    if ' NSEC3 ' in text or '\tNSEC3\t' in text: return 'nsec3'
    if ' NSEC ' in text or '\tNSEC\t' in text: return 'nsec'
    return 'unknown'

def extract_nsec_names(path, domain):
    names=[]; seen=set(); dom=domain.rstrip('.')
    for line in Path(path).read_text(errors='ignore').splitlines():
        s=line.strip()
        if not s or s.startswith(';'): continue
        owner=s.split()[0].rstrip('.').lower()
        if owner=='@': owner=dom
        elif not owner.endswith(dom): owner=f'{owner}.{dom}' if '.' not in owner else owner
        if owner.endswith(dom) and owner not in seen:
            seen.add(owner); names.append(owner)
    return names
