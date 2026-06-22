import importlib.util, subprocess, json, os
from pathlib import Path

def load():
    spec=importlib.util.spec_from_file_location('c','scripts/combine-frequency-sort-wordlists.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_combine_frequency_sort_wordlists(tmp_path):
    a=tmp_path/'a'; b=tmp_path/'b'; a.write_text('B.\na\n'); b.write_text('a\nb\nc\n')
    assert load().combine([a,b])==['a','b','c']

def test_prepare_seclists_removes_prevalence_column(tmp_path):
    src=tmp_path/'in.txt'; src.write_text('www,123\n123 www\nmail 456\napi\n')
    assets=tmp_path/'assets'
    subprocess.check_call(['bash','scripts/prepare-seclists.sh','--archive',str(src),'--assets-dir',str(assets)])
    assert (assets/'wordlists/seclists-subdomains-full-clean.txt').read_text().splitlines()==['www','www','mail','api']

def test_pcfg_metadata_written(tmp_path):
    repo=tmp_path/'repo'; repo.mkdir(); out=tmp_path/'assets/wordlists/rfc1035_pcfg_top100000000.txt'
    env=os.environ|{'PCFG_REPO':str(repo),'PCFG_OUTPUT':str(out),'PCFG_COMMAND':'printf x'}
    subprocess.check_call(['bash','scripts/generate-pcfg-wordlist.sh'], env=env)
    meta=json.loads((tmp_path/'assets/wordlists/rfc1035_pcfg_top100000000.json').read_text())
    assert meta['candidate_count']==100000000
