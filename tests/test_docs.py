from pathlib import Path

def test_docs_include_apt_dependencies():
    text=Path('docs/installation.md').read_text()
    for token in ['python3-venv','python3-dev','libssl-dev','p7zip-full','hashcat']:
        assert token in text
    assert 'gcc' in text or 'build-essential' in text

def test_seclists_sparse_checkout_command_documented():
    text=Path('docs/installation.md').read_text()+Path('scripts/bootstrap.sh').read_text()
    assert 'git sparse-checkout set Discovery/DNS' in text or 'sparse-checkout set "$path"' in text

def test_opentaal_sparse_checkout_command_documented():
    text=Path('docs/installation.md').read_text()+Path('scripts/bootstrap.sh').read_text()
    assert 'git sparse-checkout set --no-cone wordlist.txt' in text or 'sparse-checkout set --no-cone "$file_path"' in text

def test_sparse_checkout_directory_command_for_seclists():
    text=Path('scripts/bootstrap.sh').read_text()
    assert 'git -C "$dir" sparse-checkout set "$sparse_dir"' in text
    assert 'Discovery/DNS' in text

def test_sparse_checkout_file_command_for_opentaal():
    text=Path('scripts/bootstrap.sh').read_text()
    assert 'git -C "$dir" sparse-checkout set --no-cone "$file_path"' in text
    assert 'wordlist.txt' in text

def test_sparse_checkout_file_command_for_dutch_dns_wordlists():
    text=Path('scripts/bootstrap.sh').read_text()
    assert 'git -C "$dir" sparse-checkout set --no-cone "$file_path"' in text
    assert 'subsubdomains_all_by_occurrance.txt' in text

def test_docs_do_not_recommend_skip_checks():
    text='\n'.join(p.read_text() for p in Path('docs').glob('*.md'))
    assert '--skip-checks' not in text or 'do not use `--skip-checks`' in text.lower()

def test_install_docs_include_required_versions():
    text=Path('docs/installation.md').read_text()
    assert 'hashcat >= 7.1.2' in text
    assert 'amass >= 5.1.1' in text
    assert 'subfinder >= 2.14.0' in text

def test_install_docs_warn_apt_hashcat_may_be_old():
    text=Path('docs/installation.md').read_text().lower()
    assert 'apt repositories may be behind' in text and 'older than 7.1.2' in text

def test_install_docs_include_go_124_for_subfinder():
    text=Path('docs/installation.md').read_text()
    assert 'Go 1.24 or newer' in text

def test_docs_describe_combining_all_discovery_dns_wordlists():
    text=(Path('docs/dependencies.md').read_text()+Path('docs/installation.md').read_text()).lower()
    assert 'all discovery/dns `*.txt`' in text
    assert 'cleaned `subdomains-top1million-full.7z`' in text or 'cleaned subdomains-top1million-full.7z' in text
    assert 'labels split on dots' in text
    assert 'leading empty line' in text

def test_docs_include_amass_install_command():
    assert 'CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@main' in Path('docs/installation.md').read_text()

def test_docs_include_subfinder_install_command():
    assert 'go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest' in Path('docs/installation.md').read_text()

def test_docs_warn_main_and_latest_are_moving_targets():
    text=Path('docs/installation.md').read_text().lower()
    assert '@main' in text and '@latest' in text and 'version verification after install is mandatory' in text

def test_docs_do_not_reference_seclists_full_total():
    text='\n'.join(p.read_text() for p in Path('docs').glob('*.md'))
    assert 'seclists-full-total.txt' not in text

def test_readme_quickstart_does_not_call_install_and_bootstrap_sequentially():
    text=Path('README.md').read_text()
    assert 'scripts/install.sh\nscripts/bootstrap.sh' not in text
    assert 'scripts/install.sh --skip-pcfg\nscripts/bootstrap.sh' not in text

def test_install_docs_explain_venv_activation():
    assert 'source .venv/bin/activate' in Path('docs/installation.md').read_text()

def test_install_docs_show_venv_bin_alternative():
    assert '.venv/bin/nsec3-recon' in Path('docs/installation.md').read_text()

def test_bootstrap_documented_as_lower_level():
    text=Path('docs/installation.md').read_text().lower()
    assert 'lower-level dependency/bootstrap helper' in text
    assert 'normally called by `scripts/install.sh`' in text

def test_quickstart_dry_run_after_activation():
    text=Path('README.md').read_text()
    assert 'source .venv/bin/activate\nnsec3-recon --help\nnsec3-recon example.nl --dry-run' in text or '.venv/bin/nsec3-recon example.nl --dry-run' in text

def test_docs_explain_dnssec_probe_is_advisory():
    text='\n'.join(p.read_text() for p in Path('docs').glob('*.md')).lower()
    assert 'dns probe is advisory' in text
    assert 'nsec3map detect-only is authoritative' in text

def test_docs_explain_nsec3map_psycopg2_dependency():
    text=(Path('docs/installation.md').read_text()+Path('docs/troubleshooting.md').read_text()).lower()
    assert 'psycopg2-binary' in text
    assert 'nsec3map imports `psycopg2`' in text or 'nsec3map imports psycopg2' in text
    assert 'direct' in text and 'map.py' in text


def test_docs_explain_output_path_error():
    text=Path('docs/troubleshooting.md').read_text().lower()
    assert 'unable to open output file' in text
    assert 'absolute output paths' in text
    assert 'cwd' in text


def test_docs_do_not_require_nsec3map_editable_install():
    text=(Path('docs/installation.md').read_text()+Path('docs/troubleshooting.md').read_text()).lower()
    assert 'editable nsec3map installation is not required' in text or 'editable installation is not required' in text
    assert 'direct `map.py` invocation is default' in text or 'direct map.py invocation is default' in text


def test_docs_include_libpq_dev_only_as_optional():
    text=Path('docs/installation.md').read_text().lower()
    assert 'libpq-dev' in text
    assert 'optional' in text and 'source psycopg2' in text

def test_docs_explain_model_asset_preparation():
    text=(Path('docs/installation.md').read_text()+Path('docs/dependencies.md').read_text()+Path('docs/troubleshooting.md').read_text())
    assert 'deps/src/nsec3-candidate-scheduler/models' in text
    assert 'assets/models' in text
    assert 'scripts/prepare-models.sh' in text

def test_docs_document_dashboard_modes():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert '--dashboard auto|rich|plain|off' in text

def test_docs_do_not_mention_no_tui():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert '--no-tui' not in text
