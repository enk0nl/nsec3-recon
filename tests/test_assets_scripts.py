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

def test_opentaal_expected_file_path():
    assert 'deps/src/opentaal-wordlist/wordlist.txt' in Path('docs/installation.md').read_text()
    assert 'wordlist.txt' in Path('scripts/prepare-opentaal.sh').read_text()

def test_dutch_dns_expected_file_path():
    assert 'deps/src/dutch-dns-wordlists/subsubdomains_all_by_occurrance.txt' in Path('docs/installation.md').read_text()
    assert 'subsubdomains_all_by_occurrance.txt' in Path('scripts/prepare-dutch-dns-wordlists.sh').read_text()

def test_prepare_seclists_invokes_combiner_with_dns_dir_and_extra_input():
    text=Path('scripts/prepare-seclists.sh').read_text()
    assert '--input-dir "$DNS_DIR"' in text
    assert '--extra-input "$CLEAN"' in text
    assert 'seclists-subdomains-full-clean.txt' in text

def test_prepare_seclists_does_not_extract_archive_into_dns_dir():
    text=Path('scripts/prepare-seclists.sh').read_text()
    assert 'tmp=$(mktemp -d)' in text
    assert '7z" x -o"$tmp"' in text or '"$EX" x -o"$tmp"' in text

def test_prepare_seclists_outputs_final_wordlist_only_by_default(tmp_path):
    src=tmp_path/'archive.txt'; src.write_text('www\napi.example.nl\n')
    assets=tmp_path/'assets'
    subprocess.check_call(['bash','scripts/prepare-seclists.sh','--archive',str(src),'--assets-dir',str(assets)])
    assert (assets/'wordlists/seclists_total.txt').exists()
    assert not (assets/'wordlists/seclists_total_counts.tsv').exists()
    assert not (assets/'wordlists/seclists-full-total.txt').exists()
    assert (assets/'wordlists/seclists_total.txt').read_bytes().startswith(b'\n')

def test_prevalence_cleaner_formats(tmp_path):
    src=tmp_path/'in.txt'; src.write_text('www,123\n123,www\nwww 123\n123 www\napi\n')
    assets=tmp_path/'assets'
    subprocess.check_call(['bash','scripts/prepare-seclists.sh','--archive',str(src),'--assets-dir',str(assets)])
    assert (assets/'wordlists/seclists-subdomains-full-clean.txt').read_text().splitlines()==['www','www','www','www','api']

def test_install_go_tools_uses_amass_main_command():
    assert 'CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@main' in Path('scripts/install.sh').read_text()

def test_install_go_tools_uses_subfinder_latest_command():
    assert 'go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest' in Path('scripts/install.sh').read_text()

def test_install_go_tools_verifies_versions_after_install():
    text=Path('scripts/install.sh').read_text()
    assert 'scripts/check-tools.sh --strict' in text
    assert 'AMASS_BIN="$HOME/go/bin/amass"' in text
    assert 'SUBFINDER_BIN="$HOME/go/bin/subfinder"' in text


def test_seclists_keep_counts_option_writes_counts_file(tmp_path):
    src=tmp_path/'archive.txt'; src.write_text('www\napi.example.nl\n')
    assets=tmp_path/'assets'
    subprocess.check_call(['bash','scripts/prepare-seclists.sh','--archive',str(src),'--assets-dir',str(assets),'--keep-counts'])
    assert (assets/'wordlists/seclists_total_counts.tsv').exists()

def test_seclists_no_compat_symlink_by_default(tmp_path):
    src=tmp_path/'archive.txt'; src.write_text('www\n')
    assets=tmp_path/'assets'
    subprocess.check_call(['bash','scripts/prepare-seclists.sh','--archive',str(src),'--assets-dir',str(assets)])
    assert not (assets/'wordlists/seclists-full-total.txt').exists()

def test_install_script_verifies_cli_entrypoint():
    assert '.venv/bin/nsec3-recon --help' in Path('scripts/install.sh').read_text()

def test_install_script_prints_next_steps():
    text=Path('scripts/install.sh').read_text()
    assert 'source .venv/bin/activate' in text
    assert 'nsec3-recon --help' in text
    assert '.venv/bin/nsec3-recon' in text
