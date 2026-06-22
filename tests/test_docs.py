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
    assert 'git sparse-checkout set wordlist.txt' in text or 'sparse-checkout set "$path"' in text
