from __future__ import annotations
from dataclasses import dataclass
import re

_SLICE_RE = re.compile(r"^\[(?P<idx>\d+)/(?:\s*)?(?P<total>\d+)\]\s+(?P<schedule>\S+)\s+(?P<arm>\S+)(?P<rest>.*)$")
_PAIR_RE = re.compile(r"(?P<key>[a-zA-Z_][\w-]*)=(?P<value>\S+)")

@dataclass
class SchedulerParseResult:
    parsed: bool
    line: str
    data: dict


def _to_int(v):
    try: return int(v)
    except Exception: return None

def _to_float(v):
    try: return float(str(v).rstrip('s%'))
    except Exception: return None

def _split_transition(v):
    if not v or '->' not in v: return (None, None)
    a,b = v.split('->',1)
    return a,b

def _split_required(v):
    if not v: return (None, None)
    sep = '/' if '/' in v else (':' if ':' in v else None)
    if not sep: return (_to_int(v), None)
    a,b = v.split(sep,1)
    return _to_int(a), _to_int(b)

def parse_scheduler_line(line: str) -> SchedulerParseResult:
    text = (line or '').strip()
    m = _SLICE_RE.match(text)
    if not m:
        return SchedulerParseResult(False, text, {'message': text})
    data = {
        'slice_index': _to_int(m.group('idx')),
        'total_slices': _to_int(m.group('total')),
        'schedule_name': m.group('schedule'),
        'arm': m.group('arm'),
        'raw': text,
    }
    kv = {mm.group('key'): mm.group('value') for mm in _PAIR_RE.finditer(m.group('rest') or '')}
    data['reason'] = kv.get('reason')
    for key in ('written','enq','new','total'):
        if key in kv: data[key] = _to_int(kv[key])
    if 'reward' in kv: data['reward'] = _to_float(kv['reward'])
    if 'runtime' in kv: data['runtime_seconds'] = _to_float(kv['runtime'])
    if 'progress' in kv: data['progress'] = kv['progress']
    if 'queue' in kv:
        a,b = _split_transition(kv['queue']); data['queue_before'] = _to_int(a); data['queue_after'] = _to_int(b)
    if 'score' in kv:
        a,b = _split_transition(kv['score']); data['score_before'] = _to_float(a); data['score_after'] = _to_float(b)
    if 'skip' in kv:
        a,b = _split_transition(kv['skip']); data['skip_before'] = _to_int(a); data['skip_after'] = _to_int(b)
    if 'gate_queue' in kv:
        a,b = _split_required(kv['gate_queue']); data['gate_queue_current'] = a; data['gate_queue_required'] = b
    if 'cooldown' in kv:
        a,b = _split_required(kv['cooldown']); data['cooldown_current'] = a; data['cooldown_required'] = b
    return SchedulerParseResult(True, text, data)
