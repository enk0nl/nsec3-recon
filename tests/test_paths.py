import os
from pathlib import Path
from nsec3_recon.paths import expand_user_path
from nsec3_recon.adapters.tools import resolve_osint_binary
from nsec3_recon.adapters.scheduler import render_scheduler_config


def test_no_home_vboxuser_hardcoded():
    roots=[Path('src'), Path('scripts'), Path('docs'), Path('tests'), Path('README.md')]
    text='\n'.join(p.read_text(errors='ignore') for root in roots for p in ([root] if root.is_file() else root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts)
    forbidden = '/home/' + 'vboxuser'
    assert forbidden not in text


def test_expand_user_path_tilde():
    assert expand_user_path('~/go/bin/amass') == str(Path.home() / 'go/bin/amass')


def test_expand_user_path_home_env():
    assert expand_user_path('$HOME/go/bin/subfinder') == str(Path.home() / 'go/bin/subfinder')


def test_scheduler_config_renders_osint_binary_paths(tmp_path):
    amass=tmp_path/'tools/amass'; subfinder=tmp_path/'tools/subfinder'
    amass.parent.mkdir(); amass.write_text(''); subfinder.write_text('')
    cfg=render_scheduler_config('example.nl', tmp_path/'assets', tmp_path/'cfg.json', amass_bin=str(amass), subfinder_bin=str(subfinder))
    arms={a['name']:a for a in cfg['arms']}
    assert arms['osint/amass']['amass_binary'] == str(amass)
    assert arms['osint/subfinder']['subfinder_binary'] == str(subfinder)


def test_tool_lookup_prefers_configured_path():
    assert resolve_osint_binary('/opt/tools/amass', 'amass', '~/go/bin/amass') == '/opt/tools/amass'


def test_tool_lookup_falls_back_to_home_go_bin(monkeypatch, tmp_path):
    home=tmp_path/'home'; tool=home/'go/bin/amass'; tool.parent.mkdir(parents=True); tool.write_text('')
    monkeypatch.setenv('HOME', str(home))
    assert resolve_osint_binary('~/go/bin/amass', 'amass', '~/go/bin/amass') == str(tool)


def test_tool_lookup_falls_back_to_path(monkeypatch, tmp_path):
    tool=tmp_path/'amass'; tool.write_text(''); tool.chmod(0o755)
    monkeypatch.setenv('HOME', str(tmp_path/'empty-home'))
    monkeypatch.setenv('PATH', str(tmp_path))
    assert resolve_osint_binary('~/go/bin/amass', 'amass', '~/go/bin/amass') == 'amass'
