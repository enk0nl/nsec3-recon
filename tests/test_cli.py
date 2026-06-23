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

def test_cli_default_hashcat_optimized_settings():
    from nsec3_recon.cli import build_parser
    args = build_parser().parse_args(['example.nl'])
    assert args.hashcat_optimized_kernels is True
    assert args.hashcat_optimized_kernel_failover is True

def test_cli_no_hashcat_optimized_kernel_flags(tmp_path, capsys):
    out = tmp_path / 'run'
    assert main(['example.nl','--dry-run','--out-dir',str(out),'--dashboard','plain','--no-hashcat-optimized-kernels','--no-hashcat-optimized-kernel-failover']) == 0
    text = capsys.readouterr().out
    assert 'Hashcat optimized kernels: disabled' in text
    assert 'Hashcat optimized-kernel failover: disabled' in text
    assert '--no-optimized-kernels' in text
    assert '--no-optimized-kernel-failover' in text
    import json
    cfg = json.loads((out/'config/scheduler_config.json').read_text())
    assert cfg['hashcat']['optimized_kernels'] is False
    assert cfg['hashcat']['optimized_kernel_failover'] is False

def test_cli_default_nsec3map_hashlimit_is_zero(tmp_path, capsys):
    import json
    out = tmp_path / 'run'
    assert main(['example.nl','--dry-run','--out-dir',str(out),'--dashboard','plain']) == 0
    cfg = json.loads((out/'config/pipeline_config.json').read_text())
    summary = json.loads((out/'reports/summary.json').read_text())
    stdout = capsys.readouterr().out
    assert cfg['nsec3map_hashlimit'] == 0
    assert summary['nsec3map_hashlimit'] == 0
    assert 'nsec3map hashlimit: 0' in stdout


def test_cli_accepts_nsec3map_hashlimit_positive_value(tmp_path, capsys):
    import json
    out = tmp_path / 'run'
    assert main(['example.nl','--dry-run','--out-dir',str(out),'--dashboard','plain','--nsec3map-hashlimit','10000']) == 0
    cfg = json.loads((out/'config/pipeline_config.json').read_text())
    summary = json.loads((out/'reports/summary.json').read_text())
    stdout = capsys.readouterr().out
    assert cfg['nsec3map_hashlimit'] == 10000
    assert summary['nsec3map_hashlimit'] == 10000
    assert 'nsec3map hashlimit: 10000' in stdout
    assert '--hashlimit=10000' in stdout


def test_cli_rejects_negative_nsec3map_hashlimit(tmp_path, capsys):
    out = tmp_path / 'run'
    assert main(['example.nl','--nsec3map-hashlimit','-1','--out-dir',str(out)]) == 2
    err = capsys.readouterr().err
    assert 'nsec3map hashlimit must be >= 0' in err
    assert not out.exists()
