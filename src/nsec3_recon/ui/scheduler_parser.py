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
        'source': 'stdout',
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
        if '->' in kv['score']:
            a,b = _split_transition(kv['score']); data['score_before'] = _to_float(a); data['score_after'] = _to_float(b)
        else:
            data['score_after'] = _to_float(kv['score'])
    if 'skip' in kv:
        a,b = _split_transition(kv['skip']); data['skip_before'] = _to_int(a); data['skip_after'] = _to_int(b)
    if 'gate_queue' in kv:
        a,b = _split_required(kv['gate_queue']); data['gate_queue_current'] = a; data['gate_queue_required'] = b
    if 'cooldown' in kv:
        a,b = _split_required(kv['cooldown']); data['cooldown_current'] = a; data['cooldown_required'] = b
    return SchedulerParseResult(True, text, data)

def _first(record, *keys):
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


_OSINT_START_RE = re.compile(r"\[osint\]\s+(?P<arm>osint/(?:subfinder|amass))\s+completed\b")
_OSINT_BOUNDARY_RE = re.compile(r"\s+(?=(?:\[osint\]\s+osint/(?:subfinder|amass)\s+completed\b|\[\d+/\d+\]))")

def _parse_osint_status_fragment(fragment: str) -> dict | None:
    text = (fragment or '').strip()
    m = _OSINT_START_RE.search(text)
    if not m:
        return None
    try:
        arm = m.group('arm')
        tool = arm.rsplit('/', 1)[-1]
        kv_text = text[m.end():]
        kv = {mm.group('key'): mm.group('value') for mm in _PAIR_RE.finditer(kv_text)}
        return {
            'type': 'osint_status',
            'arm': arm,
            'tool': tool,
            'status': kv.get('status'),
            'raw_count': _to_int(_first(kv, 'raw', 'raw_count')),
            'candidate_count': _to_int(_first(kv, 'candidates', 'candidate_count')),
            'exit_code': _to_int(kv.get('exit_code')),
            'reason': kv.get('reason'),
            'wordlist': kv.get('wordlist'),
            'raw': text,
            'source': 'stdout',
        }
    except Exception:
        return None

def parse_osint_status_lines(text: str) -> list[dict]:
    source = text or ''
    matches = list(_OSINT_START_RE.finditer(source))
    if not matches:
        return []
    out=[]
    for idx, match in enumerate(matches):
        next_osint = matches[idx + 1].start() if idx + 1 < len(matches) else len(source)
        boundary = _OSINT_BOUNDARY_RE.search(source, match.end(), next_osint)
        end = boundary.start() if boundary else next_osint
        parsed = _parse_osint_status_fragment(source[match.start():end])
        if parsed:
            out.append(parsed)
    return out

def parse_osint_status_line(line: str) -> dict | None:
    parsed = parse_osint_status_lines(line)
    return parsed[0] if parsed else None

def normalize_scheduler_record(record: dict) -> SchedulerParseResult | None:
    """Normalize scheduler jobs.jsonl records into dashboard slice data.

    jobs.jsonl is preferred for aggregation because it can include warm-up and
    other non-adaptive runs whose stdout line format may differ from adaptive
    slice output. Records without an arm and at least one scheduler-run metric
    are ignored as metadata/status records.
    """
    if not isinstance(record, dict):
        return None
    arm = _first(record, 'arm', 'arm_name', 'arm_type')
    new_keys=('shared_new_cracks', 'marginal_new_cracks', 'new_cracks', 'new_discoveries', 'discoveries', 'new')
    has_new = any(k in record for k in new_keys)
    if not arm or not has_new:
        return None
    if record.get('valid_work') is False:
        return None
    status = record.get('execution_status')
    if status is not None and status not in {'executed', 'valid', 'completed'}:
        return None
    phase = _first(record, 'phase', 'schedule')
    if not phase and record.get('warmup') is True:
        phase = 'warmup'
    data = {
        'phase': phase or 'unknown',
        'slice_index': _to_int(_first(record, 'slice_index', 'slice', 'index', 'job_id')),
        'total_slices': _to_int(_first(record, 'total_slices', 'slices')),
        'schedule_name': _first(record, 'schedule', 'phase') or 'jobs_jsonl',
        'arm': str(arm),
        'reason': _first(record, 'selection_reason', 'reason'),
        'new': _to_int(_first(record, *new_keys)),
        'total': _to_int(_first(record, 'total_cracks', 'total_discoveries', 'total')),
        'global_total': _to_int(_first(record, 'total_cracks', 'total_discoveries', 'total')),
        'reward': _to_float(_first(record, 'reward_used_for_score', 'reward')),
        'score_before': _to_float(_first(record, 'score_before')),
        'score_after': _to_float(_first(record, 'score_after', 'score')),
        'runtime_seconds': _to_float(_first(record, 'runtime_seconds', 'actual_runtime_seconds', 'runtime')),
        'source': 'jobs_jsonl',
        'job_id': _first(record, 'job_id', 'id', 'uuid'),
        'record_key': f"job:{_first(record, 'job_id', 'id', 'uuid')}" if _first(record, 'job_id', 'id', 'uuid') is not None else None,
        'timestamp': _first(record, 'timestamp'),
        'requested_slice_seconds': _to_float(_first(record, 'requested_slice_seconds')),
        'exit_code': _first(record, 'exit_code'),
        'exit_meaning': _first(record, 'exit_meaning'),
        'exhausted': _first(record, 'exhausted'),
        'raw_record': record,
    }
    return SchedulerParseResult(True, '', data)
