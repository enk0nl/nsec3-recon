from pathlib import Path
from nsec3_recon.cli import build_parser

def test_no_demo_profile_or_template_names(capsys):
    assert not Path('src/nsec3_recon/templates/scheduler_config.demo.json').exists()
    assert not Path('scripts/bootstrap-demo.sh').exists()
    assert not Path('scripts/install-demo.sh').exists()
    build_parser().print_help(); out=capsys.readouterr().out
    assert '--profile' not in out

def test_scheduler_config_template_name():
    assert Path('src/nsec3_recon/templates/scheduler_config.json').exists()
