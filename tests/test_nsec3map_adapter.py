from nsec3_recon.adapters.nsec3map import classify_zone_file

def test_classify_nsec3(tmp_path):
    p=tmp_path/'z'; p.write_text('x 3600 IN NSEC3 1 0 0 - ABC\n')
    assert classify_zone_file(p)=='nsec3'
