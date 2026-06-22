import types
from nsec3_recon.adapters import dns as dns_adapter


def test_dnssec_probe_records_errors(monkeypatch):
    class Timeout(Exception): pass
    class NoAnswer(Exception): pass
    class Resolver:
        def use_edns(self, **kwargs): pass
        def resolve(self, domain, rdtype, raise_on_no_answer=False):
            if rdtype == 'DNSKEY':
                raise Timeout('slow')
            raise NoAnswer('no ds')
    fake_dns = types.SimpleNamespace(
        resolver=types.SimpleNamespace(Resolver=Resolver, NoAnswer=NoAnswer, NXDOMAIN=Exception, NoNameservers=Exception),
        exception=types.SimpleNamespace(Timeout=Timeout),
        flags=types.SimpleNamespace(DO=32768),
    )
    monkeypatch.setattr(dns_adapter, '_dns', lambda: fake_dns)
    data = dns_adapter.dnssec_evidence('example.nl')
    assert data['probe_status'] == 'unknown'
    assert data['evidence']['dnskey']['status'] == 'error'
    assert 'timeout' in data['evidence']['dnskey']['error']
    assert data['evidence']['ds']['status'] == 'absent'
