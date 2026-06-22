from nsec3_recon.adapters.subprocess_runner import SubprocessRunner

def test_subprocess_runner_captures_stdout_stderr(tmp_path):
    r=SubprocessRunner().run(['python3','-c','import sys; print("o"); print("e", file=sys.stderr)'], stdout_log=tmp_path/'o', stderr_log=tmp_path/'e')
    assert r.returncode==0 and (tmp_path/'o').read_text().strip()=='o' and (tmp_path/'e').read_text().strip()=='e'
