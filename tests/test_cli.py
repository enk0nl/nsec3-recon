from nsec3_recon.cli import main

def test_cli_help(capsys):
    assert main(['--help']) == 0

def test_cli_dry_run(tmp_path, capsys):
    assert main(['example.nl','--dry-run','--out-dir',str(tmp_path/'run'),'--no-tui'])==0
    assert (tmp_path/'run/config/scheduler_config.json').exists()

def test_cli_accepts_hashcat_bin_override(tmp_path):
    from nsec3_recon.cli import main
    assert main(['example.nl','--dry-run','--no-tui','--out-dir',str(tmp_path/'run'),'--hashcat-bin','/tmp/hashcat']) == 0
    cfg=(tmp_path/'run/config/pipeline_config.json').read_text()
    assert '/tmp/hashcat' in cfg
