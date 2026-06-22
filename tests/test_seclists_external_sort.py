import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('seclists_sort', 'scripts/seclists_fqdn_and_labels_external_sort.py')
mod = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mod)

def run_combiner(tmp_path, input_dir, *args, keep_counts=False):
    out_prefix=tmp_path/'out/seclists'
    extra = ['--keep-counts'] if keep_counts else []
    mod.main(['--input-dir', str(input_dir), '--out-prefix', str(out_prefix), '--sort-memory', '1M', '--tmp-dir', str(tmp_path), *extra, *args])
    return out_prefix.with_name('seclists_total_counts.tsv'), out_prefix.with_name('seclists_total.txt')

def counts(path):
    d={}
    for line in path.read_text().splitlines():
        c,v=line.split('\t',1); d[v]=int(c)
    return d

def test_seclists_combiner_reads_all_txt_files_in_dns_dir(tmp_path):
    d=tmp_path/'dns'; d.mkdir(); (d/'a.txt').write_text('www\napi.example.nl\n'); (d/'b.txt').write_text('mail\napi.example.nl\n')
    c,v=run_combiner(tmp_path,d)
    vals=set(v.read_text().splitlines())
    assert {'api.example.nl','api','example','nl','www','mail'} <= vals

def test_seclists_combiner_includes_extra_input(tmp_path):
    d=tmp_path/'dns'; d.mkdir(); (d/'a.txt').write_text('www\n')
    extra=tmp_path/'clean-top1m.txt'; extra.write_text('vpn.example.nl\n')
    c,v=run_combiner(tmp_path,d,'--extra-input',str(extra))
    vals=set(v.read_text().splitlines())
    assert {'vpn.example.nl','vpn','example','nl'} <= vals

def test_seclists_combiner_frequency_sort(tmp_path):
    d=tmp_path/'dns'; d.mkdir(); (d/'a.txt').write_text('api.example.nl\napi.test.nl\n')
    c,v=run_combiner(tmp_path,d, keep_counts=True)
    lines=c.read_text().splitlines()
    assert lines[0].startswith('2\tapi')
    assert counts(c)['api'] > counts(c)['api.example.nl']

def test_seclists_combiner_avoids_double_count_single_label_by_default(tmp_path):
    d=tmp_path/'dns'; d.mkdir(); (d/'a.txt').write_text('www\n')
    c,v=run_combiner(tmp_path,d, keep_counts=True)
    assert counts(c)['www']==1

def test_seclists_combiner_can_double_count_single_label_when_enabled(tmp_path):
    d=tmp_path/'dns'; d.mkdir(); (d/'a.txt').write_text('www\n')
    c,v=run_combiner(tmp_path,d,'--double-count-single-labels', keep_counts=True)
    assert counts(c)['www']==2

def test_seclists_values_file_starts_with_empty_line(tmp_path):
    d=tmp_path/'dns'; d.mkdir(); (d/'a.txt').write_text('www\n')
    c,v=run_combiner(tmp_path,d)
    assert v.read_bytes().startswith(b'\n')

def test_seclists_counts_file_does_not_start_with_empty_candidate(tmp_path):
    d=tmp_path/'dns'; d.mkdir(); (d/'a.txt').write_text('www\n')
    c,v=run_combiner(tmp_path,d, keep_counts=True)
    assert c.read_text().splitlines()[0] == '1\twww'
