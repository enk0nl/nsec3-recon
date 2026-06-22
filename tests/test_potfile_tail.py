from nsec3_recon.adapters.potfile import PotfileTail

def test_potfile_tail_detects_new_cracks(tmp_path):
    p=tmp_path/'run.pot'; t=PotfileTail(p); p.write_text('h:one\n')
    assert t.poll()==['one']; p.write_text('h:one\nh2:two\n')
    assert t.poll()==['two']
