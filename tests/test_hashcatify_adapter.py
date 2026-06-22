from nsec3_recon.pipeline import PipelineError

def test_hashcatify_empty_hash_file_fails():
    assert PipelineError('hashcatify','x').stage=='hashcatify'

def test_hashcatify_uses_absolute_input_and_output_paths(tmp_path):
    from pathlib import Path
    from nsec3_recon.adapters.nsec3map import hashcatify_command
    src=tmp_path/'nsec3map'; src.mkdir(); (src/'hashcatify.py').write_text('')
    zone=tmp_path/'run/nsec3map/zone.txt'
    h=tmp_path/'run/nsec3map/nsec3map_hashfile.hash'
    cmd=hashcatify_command(src,'python',zone,h)
    assert Path(cmd[2]).is_absolute()
    assert Path(cmd[3]).is_absolute()


def test_hashcatify_creates_output_parent_dir(tmp_path):
    from nsec3_recon.adapters.nsec3map import hashcatify_command
    src=tmp_path/'nsec3map'; src.mkdir()
    out=tmp_path/'run/nsec3map/nsec3map_hashfile.hash'
    hashcatify_command(src,'python',tmp_path/'run/nsec3map/zone.txt',out)
    assert out.parent.exists()
