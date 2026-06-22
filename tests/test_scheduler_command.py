from pathlib import Path
from nsec3_recon.config import PipelineConfig

def test_scheduler_command_shape():
    cmd=PipelineConfig('example.nl').scheduler_command(Path('/w'),Path('/h'),Path('/c'))
    s=' '.join(cmd)
    assert 'python3 -m nsec3_candidate_scheduler run' in s and '--hash-mode 8300' in s and '--schedule adaptive' in s and '--total-slices' in cmd and '--slice-seconds' in cmd
