from nsec3_recon.adapters.subprocess_runner import SubprocessRunner

def test_subprocess_runner_captures_stdout_stderr(tmp_path):
    r=SubprocessRunner().run(['python3','-c','import sys; print("o"); print("e", file=sys.stderr)'], stdout_log=tmp_path/'o', stderr_log=tmp_path/'e')
    assert r.returncode==0 and (tmp_path/'o').read_text().strip()=='o' and (tmp_path/'e').read_text().strip()=='e'

def test_nsec3map_missing_psycopg2_error_message(tmp_path):
    from types import SimpleNamespace
    from nsec3_recon.stages.nsec3map_stage import _format_subprocess_failure
    err=tmp_path/'err.log'
    err.write_text("ModuleNotFoundError: No module named 'psycopg2'\n")
    msg=_format_subprocess_failure('nsec3map',['/venv/bin/python','map.py'],tmp_path,SimpleNamespace(returncode=1),err,interpreter='/venv/bin/python')
    assert 'pip install psycopg2-binary' in msg and 'Interpreter: /venv/bin/python' in msg


def test_subprocess_failure_reports_cwd_and_command(tmp_path):
    from types import SimpleNamespace
    from nsec3_recon.stages.nsec3map_stage import _format_subprocess_failure
    err=tmp_path/'err.log'; err.write_text('boom')
    msg=_format_subprocess_failure('nsec3map',['python','map.py'],tmp_path,SimpleNamespace(returncode=2),err)
    assert 'Command:' in msg and 'python map.py' in msg and 'CWD:' in msg and str(tmp_path) in msg and str(err) in msg
