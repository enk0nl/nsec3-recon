from nsec3_recon.adapters.potfile import PotfileTail

def test_potfile_tail_detects_new_cracks(tmp_path):
    p=tmp_path/'run.pot'; t=PotfileTail(p); p.write_text('h:one\n')
    assert t.poll()==['one']; p.write_text('h:one\nh2:two\n')
    assert t.poll()==['two']

def test_potfile_tail_maps_empty_plaintext_to_at(tmp_path):
    p=tmp_path/'run.pot'; t=PotfileTail(p)
    p.write_text('7c33954r9727aj5urd7vurs7nm4deftv:.example.nl:ab:1:\n')
    assert t.poll()==['@']


def test_potfile_tail_maps_space_empty_plaintext_to_at(tmp_path):
    p=tmp_path/'run.pot'; t=PotfileTail(p)
    p.write_text('7c33954r9727aj5urd7vurs7nm4deftv:.example.nl:ab:1:   \n')
    assert t.poll()==['@']


def test_potfile_tail_still_uses_rsplit_for_mode_8300(tmp_path):
    p=tmp_path/'run.pot'; t=PotfileTail(p)
    p.write_text('abcd:.example.nl:ab:1:www\n')
    assert t.poll()==['www']
    assert t.cracked_hashes_seen == {'abcd:.example.nl:ab:1'}
