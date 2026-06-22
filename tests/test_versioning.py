from nsec3_recon.versioning import parse_version, version_at_least

def test_parse_hashcat_version():
    for text in ["v7.1.2", "hashcat (v7.1.2) starting", "hashcat v7.1.2"]:
        assert parse_version(text) == (7, 1, 2)

def test_parse_amass_version():
    for text in ["amass v5.1.1", "v5.1.1"]:
        assert parse_version(text) == (5, 1, 1)

def test_parse_subfinder_version():
    for text in ["subfinder v2.14.0", "subfinder version 2.14.0"]:
        assert parse_version(text) == (2, 14, 0)

def test_version_at_least():
    assert version_at_least((7, 1, 2), (7, 1, 2))
    assert version_at_least((7, 1, 3), (7, 1, 2))
    assert not version_at_least((7, 0, 0), (7, 1, 2))
