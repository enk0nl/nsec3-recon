from nsec3_recon.cli import main

def test_cli_help(capsys):
    assert main(['--help']) == 0

def test_cli_dry_run(tmp_path, capsys):
    assert main(['example.nl','--dry-run','--out-dir',str(tmp_path/'run'),'--no-tui'])==0
    assert (tmp_path/'run/config/scheduler_config.json').exists()
