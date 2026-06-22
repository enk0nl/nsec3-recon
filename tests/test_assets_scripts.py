import importlib.util, subprocess, json, os
from pathlib import Path

def load():
    spec=importlib.util.spec_from_file_location('c','scripts/combine-frequency-sort-wordlists.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_combine_frequency_sort_wordlists(tmp_path):
    a=tmp_path/'a'; b=tmp_path/'b'; a.write_text('B.\na\n'); b.write_text('a\nb\nc\n')
    assert load().combine([a,b])==['a','b','c']

def test_prepare_seclists_removes_prevalence_column(tmp_path):
    src=tmp_path/'in.txt'; src.write_text('www,123\n123,www\nwww 123\n123 www\napi\n')
    assets=tmp_path/'assets'
    subprocess.check_call(['bash','scripts/prepare-seclists.sh','--archive',str(src),'--assets-dir',str(assets)])
    assert (assets/'wordlists/seclists-subdomains-full-clean.txt').read_text().splitlines()==['www','www','www','www','api']

def test_pcfg_metadata_written(tmp_path):
    repo=tmp_path/'repo'; (repo/'Rules/dutch_subdomains').mkdir(parents=True); (repo/'pcfg_guesser.py').write_text('print("x")')
    out=tmp_path/'assets/wordlists/rfc1035_pcfg_top100000000.txt'
    env=os.environ|{'PCFG_REPO':str(repo),'PCFG_OUTPUT':str(out)}
    subprocess.check_call(['bash','scripts/generate-pcfg-wordlist.sh'], env=env)
    meta=json.loads((tmp_path/'assets/wordlists/rfc1035_pcfg_top100000000.json').read_text())
    assert meta['candidate_count']==100000000

def test_pcfg_generation_command():
    assert 'python3 pcfg_guesser.py --rule dutch_subdomains --limit 100000000' in Path('scripts/generate-pcfg-wordlist.sh').read_text()

def test_install_script_detects_missing_venv_support():
    text=Path('scripts/install.sh').read_text()+Path('scripts/bootstrap.sh').read_text()
    assert 'ensure_python_venv_available' in text and 'python${PYVER}-venv' in text and 'python3-venv' in text

def test_no_n3map_editable_install_required():
    text=Path('scripts/bootstrap.sh').read_text()
    assert 'nsec3map editable install is intentionally skipped' in text
