from pathlib import Path
from nsec3_recon.adapters.nsec3map import classify_zone_file, detect_command, enumerate_command, parse_detect_output, hashcatify_command

def test_classify_nsec3(tmp_path):
    p=tmp_path/'z'; p.write_text('x 3600 IN NSEC3 1 0 0 - ABC\n')
    assert classify_zone_file(p)=='nsec3'

def test_nsec3map_uses_direct_map_py_by_default(tmp_path):
    cmd=enumerate_command(Path('deps/src/nsec3map'),'python3','example.nl',tmp_path/'zone.txt')
    assert cmd==['python3','map.py',f'--output={tmp_path/"zone.txt"}','example.nl']

def test_nsec3map_detect_only_command():
    assert detect_command(Path('deps/src/nsec3map'),'python3','example.nl')==['python3','map.py','--detect-only','example.nl']

def test_nsec3map_detect_only_parses_nsec():
    assert parse_detect_output('example.nl.: nsec\n','example.nl')=='nsec'

def test_nsec3map_detect_only_parses_nsec3():
    assert parse_detect_output('example.nl.: nsec3\n','example.nl')=='nsec3'

def test_hashcatify_uses_direct_source_script_when_available(tmp_path):
    src=tmp_path/'nsec3map'; src.mkdir(); (src/'hashcatify.py').write_text('')
    cmd=hashcatify_command(src,'python3',tmp_path/'z',tmp_path/'h')
    assert cmd[:2]==['python3',str(src/'hashcatify.py')]

def test_parse_detect_output_optional_trailing_dot():
    assert parse_detect_output('example.nl: nsec3\n','example.nl')=='nsec3'

def test_nsec3map_detect_command_uses_configured_python():
    assert detect_command(Path('deps/src/nsec3map'),'/tmp/venv/bin/python','example.nl')==['/tmp/venv/bin/python','map.py','--detect-only','example.nl']


def test_nsec3map_enumeration_command_uses_configured_python(tmp_path):
    cmd=enumerate_command(Path('deps/src/nsec3map'),'/tmp/venv/bin/python','example.nl',tmp_path/'zone.txt')
    assert cmd[0]=='/tmp/venv/bin/python'


def test_nsec3map_enumeration_uses_absolute_output_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rel=Path('runs/example.nl-test/nsec3map/zone.txt')
    cmd=enumerate_command(Path('deps/src/nsec3map'),'python','example.nl',rel)
    assert cmd[2].startswith('--output=/')
    assert '--output=runs/example.nl-test/nsec3map/zone.txt' not in cmd[2]


def test_nsec3map_enumeration_creates_output_parent_dir(tmp_path):
    zone=tmp_path/'run/nsec3map/zone.txt'
    enumerate_command(Path('deps/src/nsec3map'),'python','example.nl',zone)
    assert zone.parent.exists()
