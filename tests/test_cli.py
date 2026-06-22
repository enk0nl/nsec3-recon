from nsec3_recon.cli import main

def test_cli_help(capsys):
    assert main(['--help']) == 0

def test_cli_dry_run(tmp_path, capsys):
    assert main(['example.nl','--dry-run','--out-dir',str(tmp_path/'run'),'--dashboard','plain'])==0
    assert (tmp_path/'run/config/scheduler_config.json').exists()

def test_cli_accepts_hashcat_bin_override(tmp_path):
    from nsec3_recon.cli import main
    assert main(['example.nl','--dry-run','--dashboard','plain','--out-dir',str(tmp_path/'run'),'--hashcat-bin','/tmp/hashcat']) == 0
    cfg=(tmp_path/'run/config/pipeline_config.json').read_text()
    assert '/tmp/hashcat' in cfg

def test_nsec3map_python_default_is_sys_executable():
    import sys
    from nsec3_recon.config import PipelineConfig
    assert PipelineConfig('example.nl').nsec3map_python == sys.executable
    from nsec3_recon.cli import build_parser
    assert build_parser().parse_args(['example.nl']).nsec3map_python == sys.executable
