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
    assert 'git sparse-checkout set --no-cone /wordlist.txt' in text or 'sparse_file_pattern' in text

def test_sparse_checkout_directory_command_for_seclists():
    text=Path('scripts/bootstrap.sh').read_text()
    assert 'git -C "$dir" sparse-checkout set "$sparse_dir"' in text
    assert 'Discovery/DNS' in text

def test_sparse_checkout_file_command_for_opentaal():
    text=Path('scripts/bootstrap.sh').read_text()
    assert 'git -C "$dir" sparse-checkout set --no-cone "$sparse_file_pattern"' in text
    assert 'wordlist.txt' in text

def test_sparse_checkout_file_command_for_dutch_dns_wordlists():
    text=Path('scripts/bootstrap.sh').read_text()
    assert 'git -C "$dir" sparse-checkout set --no-cone "$sparse_file_pattern"' in text
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

def test_no_current_slice_label_in_docs():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'Current slice' not in text and 'current/previous slice' not in text

def test_docs_explain_last_completed_slice_semantics():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'scheduler slice lines are emitted after completion' in text.lower()
    assert 'Last completed slice' in text and 'Previous completed slice' in text

def test_docs_use_discovered_names_terminology():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'Discovered names' in text
    assert 'Recovered candidates' not in text and 'recovered candidates' not in text

def test_docs_explain_arm_table_columns():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'R = latest reward' in text
    assert 'Score = latest scheduler score' in text

def test_docs_explain_total_vs_global_total():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'sum of per-slice `new` values' in text
    assert 'scheduler line field `total` is the global discovered/cracked total' in text

def test_docs_explain_warmup_included_in_arm_total():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'warm-up slices are included in arm Total' in text

def test_docs_explain_jobs_jsonl_dashboard_source():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'scheduler/jobs.jsonl' in text and 'stdout parsing remains a live fallback' in text

def test_docs_do_not_show_nsec3_as_per_row_discovered_name_column():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert '07:12:02  nsec3' not in text

def test_docs_explain_jobs_jsonl_warmup_fields():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    for token in ('shared_new_cracks','new_cracks','reward_used_for_score','phase=warmup'):
        assert token in text

def test_docs_explain_discovery_sources():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert '`axfr`, `nsec`, and `nsec3`' in text

def test_docs_do_not_call_run_pot_a_discovery_source():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'run.pot` is an artifact file, not a discovery source label' in text

def test_docs_explain_slice_index_and_global_total():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert '`18/150` is the job or slice index out of configured scheduler total slices' in text
    assert '`total=218` inside slice details is the global cracked-hash count' in text

def test_docs_explain_nsec3_hash_progress():
    from pathlib import Path
    text='\n'.join(p.read_text() for p in [Path('README.md'), *Path('docs').glob('*.md')])
    assert 'cracked hashes / total hashes' in text and 'hashcatify `hash_count`' in text


def test_docs_single_file_sparse_checkout_uses_leading_slash():
    text=Path('docs/installation.md').read_text()+Path('docs/dependencies.md').read_text()
    assert 'git sparse-checkout set --no-cone /wordlist.txt' in text
    assert 'git sparse-checkout set --no-cone /subsubdomains_all_by_occurrance.txt' in text

def test_docs_do_not_recommend_non_slash_single_file_sparse_patterns():
    text=Path('docs/installation.md').read_text()+Path('docs/dependencies.md').read_text()
    assert 'git sparse-checkout set --no-cone wordlist.txt' not in text
    assert 'git sparse-checkout set --no-cone subsubdomains_all_by_occurrance.txt' not in text

def test_docs_warn_seclists_and_pcfg_are_long_running():
    text=(Path('docs/installation.md').read_text()+Path('docs/dependencies.md').read_text()).lower()
    assert 'seclists combining can take several minutes' in text
    assert 'pcfg top 100m generation can take a long time' in text

def test_dashboard_docs_explain_osint_candidate_vs_discovered():
    text='\n'.join(p.read_text() for p in Path('docs').glob('*.md'))
    assert 'OSINT returns candidate names' in text
    assert 'Discovered names are AXFR/NSEC/NSEC3-validated outputs' in text


def test_docs_do_not_use_long_prefix():
    text='\n'.join(p.read_text() for p in Path('docs').glob('*.md'))
    assert '[long]' not in text

def test_docs_describe_long_running_tasks_with_info_prefix():
    text=Path('docs/installation.md').read_text()+Path('docs/dependencies.md').read_text()
    assert '[info] Preparing SecLists DNS wordlist' in text
    assert '[info] Generating PCFG DNS wordlist' in text


def test_quickstart_default_install_does_not_skip_pcfg():
    text=Path('README.md').read_text()
    assert 'scripts/install.sh\nsource .venv/bin/activate' in text
    quickstart=text.split('## Runtime model', 1)[0]
    assert 'scripts/install.sh --skip-pcfg' not in quickstart


def test_skip_pcfg_documented_only_as_advanced_option():
    docs_text = [p.read_text() for p in Path('docs').glob('*.md')]
    text='\n'.join([Path('README.md').read_text(), *docs_text])
    assert '--skip-pcfg' in text
    assert 'Use `--skip-pcfg` only for development, CI shortcuts, or debugging' in text
    quickstart=Path('README.md').read_text().split('## Runtime model', 1)[0]
    assert '--skip-pcfg' not in quickstart


def test_dashboard_docs_do_not_document_names_footer_field():
    text=(Path('docs/dashboard.md').read_text()+Path('README.md').read_text()).lower()
    assert 'names=' not in text


def test_seen_column_documented():
    text='\n'.join(p.read_text() for p in Path('docs').glob('*.md'))
    assert (
        'Seen` is the last scheduler job/slice id where the arm produced a valid, scored '
        '`jobs.jsonl` record'
    ) in text
    assert 'recency/debug field' in text


def test_docs_mention_default_configuration_tuned_for_dutch_domains():
    text=(
        Path('README.md').read_text()
        +Path('docs/configuration.md').read_text()
        +Path('docs/usage.md').read_text()
    )
    assert 'default configuration is tuned for Dutch domains' in text
    assert '`.nl` namespace' in text
    assert 'candidate sources and scheduler configuration' in text
