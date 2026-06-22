from nsec3_recon.adapters.scheduler import render_scheduler_config

def test_scheduler_config_renders_domain_for_osint(tmp_path):
    d=render_scheduler_config('example.nl', tmp_path/'assets', tmp_path/'cfg.json')
    arms={a['name']:a for a in d['arms']}
    assert arms['osint/subfinder']['domain']=='example.nl'
    assert arms['osint/amass']['domains']=='example.nl'

def test_scheduler_config_resolves_asset_paths(tmp_path):
    d=render_scheduler_config('example.nl', tmp_path/'assets', tmp_path/'cfg.json')
    vals=[a.get('wordlist') or a.get('model') or a.get('prefixes') for a in d['arms'] if a.get('wordlist') or a.get('model') or a.get('prefixes')]
    assert all(v.startswith(str(tmp_path/'assets')) for v in vals)
