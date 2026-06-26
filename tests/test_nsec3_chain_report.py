import csv

from nsec3_recon.config import PipelineConfig
from nsec3_recon.events import EventSink
from nsec3_recon.pipeline import PipelineContext
from nsec3_recon.stages.scheduler_stage import write_discovery_reports
from nsec3_recon.workspace import Workspace
from nsec3_recon.nsec3_chain_report import NSEC3_CHAIN_HEADER, parse_potfile_cracks


def make_ctx(tmp_path, zone='example.nl', zone_text='', pot_text=''):
    ws = Workspace.create(zone, tmp_path / 'r')
    z = ws.root / 'nsec3map/zone.txt'; z.parent.mkdir(parents=True, exist_ok=True); z.write_text(zone_text, encoding='utf-8')
    p = ws.root / 'scheduler/run.pot'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(pot_text, encoding='utf-8')
    ctx = PipelineContext(PipelineConfig(zone, out_dir=tmp_path / 'r'), ws, EventSink(ws.root / 'events.jsonl'))
    write_discovery_reports(ctx)
    return ctx


def read_rows(ctx):
    with (ctx.workspace.root / 'reports/nsec3_chain.tsv').open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def hashes(ctx):
    return [row['hash'] for row in read_rows(ctx)]


def test_nsec3_chain_report_includes_cracked_and_uncracked_rows(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='''h1.example.nl. 3600 IN NSEC3 1 0 1 ab h2 A RRSIG
h2.example.nl. 3600 IN NSEC3 1 0 1 ab h3 AAAA
h3.example.nl. 3600 IN NSEC3 1 0 1 ab h1 MX
''', pot_text='h1:.example.nl:ab:1:www\n')
    rows = read_rows(ctx)
    assert len(rows) == 3
    assert [r['status'] for r in rows].count('cracked') == 1
    assert [r['status'] for r in rows].count('uncracked') == 2


def test_nsec3_chain_report_preserves_empty_plaintext_apex(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='h1.example.nl. 3600 IN NSEC3 1 0 1 ab h2 NS SOA\n', pot_text='h1:.example.nl:ab:1:\n')
    row = read_rows(ctx)[0]
    assert row['status'] == 'cracked'
    assert row['plaintext'] == ''
    assert row['fqdn'] == 'example.nl'


def test_nsec3_chain_report_expands_relative_plaintext_to_fqdn(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='h1.example.nl. 3600 IN NSEC3 1 0 1 ab h2 A\n', pot_text='h1:.example.nl:ab:1:www\n')
    row = read_rows(ctx)[0]
    assert row['plaintext'] == 'www'
    assert row['fqdn'] == 'www.example.nl'


def test_nsec3_chain_report_does_not_double_append_zone(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='h1.example.nl. 3600 IN NSEC3 1 0 1 ab h2 A\n', pot_text='h1:.example.nl:ab:1:www.example.nl\n')
    row = read_rows(ctx)[0]
    assert row['fqdn'] == 'www.example.nl'
    assert row['fqdn'] != 'www.example.nl.example.nl'


def test_nsec3_chain_report_uses_rsplit_for_potfile(tmp_path):
    pot = tmp_path / 'run.pot'; pot.write_text('h1:.example.nl:ab:1:www\n', encoding='utf-8')
    cracks = parse_potfile_cracks(pot)
    assert cracks['h1'] == 'www'
    assert cracks['h1:.example.nl:ab:1'] == 'www'


def test_nsec3_chain_report_header_has_no_index(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='h1.example.nl. 3600 IN NSEC3 1 0 1 ab h2 A\n')
    header = (ctx.workspace.root / 'reports/nsec3_chain.tsv').read_text(encoding='utf-8').splitlines()[0].split('\t')
    assert header == NSEC3_CHAIN_HEADER
    assert 'index' not in header
    assert 'source' not in header


def test_nsec3_chain_report_unavailable_fields_are_empty(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='h1.example.nl. 3600 IN NSEC3\n')
    row = read_rows(ctx)[0]
    assert row['next_hash'] == row['algorithm'] == row['flags'] == row['iterations'] == row['salt'] == row['rrtypes'] == ''
    text = (ctx.workspace.root / 'reports/nsec3_chain.tsv').read_text(encoding='utf-8')
    assert 'None' not in text and 'unknown' not in text and 'null' not in text


def test_existing_discovered_names_report_unchanged(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='h1.example.nl. 3600 IN NSEC3 1 0 1 ab h2 A\n', pot_text='h1:.example.nl:ab:1:www\n')
    assert (ctx.workspace.root / 'reports/nsec3_chain.tsv').exists()
    assert (ctx.workspace.root / 'reports/discovered_names.txt').read_text(encoding='utf-8').splitlines() == ['www.example.nl']


def test_nsec3_chain_report_orders_rows_by_next_hash_links(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='''b.example.nl. 3600 IN NSEC3 1 0 1 ab c A
    a.example.nl. 3600 IN NSEC3 1 0 1 ab b A
    c.example.nl. 3600 IN NSEC3 1 0 1 ab a A
    ''')
    assert hashes(ctx) == ['a', 'b', 'c']


def test_nsec3_chain_report_wraps_at_start_without_duplicate(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='''a.example.nl. 3600 IN NSEC3 1 0 1 ab b A
    b.example.nl. 3600 IN NSEC3 1 0 1 ab c A
    c.example.nl. 3600 IN NSEC3 1 0 1 ab a A
    ''')
    assert hashes(ctx) == ['a', 'b', 'c']


def test_nsec3_chain_report_appends_unvisited_broken_component(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='''a.example.nl. 3600 IN NSEC3 1 0 1 ab b A
    b.example.nl. 3600 IN NSEC3 1 0 1 ab a A
    x.example.nl. 3600 IN NSEC3 1 0 1 ab y A
    ''')
    assert hashes(ctx) == ['a', 'b', 'x']


def test_nsec3_chain_report_handles_missing_next_hash(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='a.example.nl. 3600 IN NSEC3 1 0 1 ab\n')
    rows = read_rows(ctx)
    assert len(rows) == 1
    assert rows[0]['hash'] == 'a'
    assert rows[0]['next_hash'] == ''


def test_nsec3_chain_report_handles_self_loop(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='a.example.nl. 3600 IN NSEC3 1 0 1 ab a A\n')
    assert hashes(ctx) == ['a']


def test_nsec3_chain_report_normalizes_hash_case_for_linking(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='''A.example.nl. 3600 IN NSEC3 1 0 1 ab b A
    B.example.nl. 3600 IN NSEC3 1 0 1 ab A A
    ''')
    assert hashes(ctx) == ['a', 'b']


def test_nsec3_chain_report_keeps_crack_annotations_after_reordering(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='''b.example.nl. 3600 IN NSEC3 1 0 1 ab c A
    a.example.nl. 3600 IN NSEC3 1 0 1 ab b A
    c.example.nl. 3600 IN NSEC3 1 0 1 ab a A
    ''', pot_text='b:.example.nl:ab:1:www\n')
    rows = read_rows(ctx)
    assert [r['hash'] for r in rows] == ['a', 'b', 'c']
    assert rows[1]['status'] == 'cracked'
    assert rows[1]['plaintext'] == 'www'
    assert rows[1]['fqdn'] == 'www.example.nl'


def test_nsec3_chain_report_empty_plaintext_apex_still_correct_after_reordering(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='''b.example.nl. 3600 IN NSEC3 1 0 1 ab a A
    a.example.nl. 3600 IN NSEC3 1 0 1 ab b A
    ''', pot_text='b:.example.nl:ab:1:\n')
    rows = read_rows(ctx)
    assert rows[1]['hash'] == 'b'
    assert rows[1]['status'] == 'cracked'
    assert rows[1]['plaintext'] == ''
    assert rows[1]['fqdn'] == 'example.nl'


def test_nsec3_chain_report_writes_all_unique_rows_once(tmp_path):
    ctx = make_ctx(tmp_path, zone_text='''c.example.nl. 3600 IN NSEC3 1 0 1 ab a A
    a.example.nl. 3600 IN NSEC3 1 0 1 ab b A
    b.example.nl. 3600 IN NSEC3 1 0 1 ab c A
    b.example.nl. 3600 IN NSEC3 1 0 1 ab c MX
    x.example.nl. 3600 IN NSEC3 1 0 1 ab A A
    ''')
    got = hashes(ctx)
    assert len(got) == 4
    assert len(got) == len(set(got))
    assert set(got) == {'a', 'b', 'c', 'x'}
