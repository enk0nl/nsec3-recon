import json
from nsec3_recon.events import EventSink

def test_events_written_jsonl(tmp_path):
    s=EventSink(tmp_path/'events.jsonl'); s.emit('x','started','msg')
    assert json.loads((tmp_path/'events.jsonl').read_text())['stage']=='x'
