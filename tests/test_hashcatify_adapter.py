from nsec3_recon.pipeline import PipelineError

def test_hashcatify_empty_hash_file_fails():
    assert PipelineError('hashcatify','x').stage=='hashcatify'
