from nsec3_recon.workspace import Workspace
from nsec3_recon.config import normalize_domain

def test_workspace_creation(tmp_path):
    ws=Workspace.create('example.nl', tmp_path/'run')
    for d in ['probe','axfr','nsec3map','scheduler/hashcat_logs','config','reports']:
        assert (ws.root/d).is_dir()

def test_domain_normalization(): assert normalize_domain('Example.NL.')=='example.nl'
