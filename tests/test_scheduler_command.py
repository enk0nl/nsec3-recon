from pathlib import Path
from nsec3_recon.config import PipelineConfig

def test_scheduler_command_shape():
    cmd=PipelineConfig('example.nl').scheduler_command(Path('/w'),Path('/h'),Path('/c'))
    s=' '.join(cmd)
    assert 'python3 -m nsec3_candidate_scheduler run' in s and '--hash-mode 8300' in s and '--schedule adaptive' in s and '--total-slices' in cmd and '--slice-seconds' in cmd

def test_scheduler_uses_absolute_paths(tmp_path):
    from pathlib import Path
    from nsec3_recon.config import PipelineConfig
    cfg=PipelineConfig('example.nl')
    cmd=cfg.scheduler_command(tmp_path/'run', tmp_path/'run/nsec3map/h.hash', tmp_path/'run/config/scheduler_config.json')
    for flag in ('--hashes','--config','--out-dir'):
        val=cmd[cmd.index(flag)+1]
        assert Path(val).is_absolute()
