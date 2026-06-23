from __future__ import annotations


def _dns():
    import dns.exception, dns.flags, dns.query, dns.resolver, dns.zone
    return dns


def _resolver(timeout=3.0, lifetime=10.0):
    dns=_dns(); r=dns.resolver.Resolver(); r.timeout=timeout; r.lifetime=lifetime; return r


def authoritative_nameservers(domain, timeout=3.0, lifetime=10.0):
    dns=_dns(); resolver=_resolver(timeout, lifetime); out=[]
    for rr in resolver.resolve(domain,'NS'):
        name=str(rr.target).rstrip('.')
        addrs=[]
        for typ in ('A','AAAA'):
            try: addrs += [str(a) for a in resolver.resolve(name,typ)]
            except Exception: pass
        out.append({'name':name,'addresses':addrs})
    return out


def _query_evidence(resolver, dns, domain, rdtype):
    result = {'present': False, 'status': 'absent', 'error': None}
    try:
        ans = resolver.resolve(domain, rdtype, raise_on_no_answer=False)
        if getattr(ans, 'rrset', None):
            result.update({'present': True, 'status': 'present'})
        else:
            result.update({'present': False, 'status': 'absent'})
    except getattr(dns.exception, 'Timeout') as e:
        result.update({'status': 'error', 'error': f'timeout: {e}'})
    except getattr(dns.resolver, 'NoAnswer') as e:
        result.update({'status': 'absent', 'error': str(e) or None})
    except getattr(dns.resolver, 'NoNameservers') as e:
        result.update({'status': 'error', 'error': f'nameserver failure: {e}'})
    except getattr(dns.resolver, 'NXDOMAIN') as e:
        result.update({'status': 'error', 'error': f'NXDOMAIN: {e}'})
    except Exception as e:
        result.update({'status': 'error', 'error': f'{type(e).__name__}: {e}'})
    return result


def dnssec_evidence(domain, timeout=3.0, lifetime=10.0):
    dns=_dns(); resolver=_resolver(timeout, lifetime)
    try:
        resolver.use_edns(edns=0, ednsflags=dns.flags.DO)
    except Exception:
        pass
    dnskey = _query_evidence(resolver, dns, domain, 'DNSKEY')
    ds = _query_evidence(resolver, dns, domain, 'DS')
    enabled = dnskey['present'] or ds['present']
    status = 'enabled' if enabled else ('unknown' if dnskey['status'] == 'error' or ds['status'] == 'error' else 'not_detected')
    return {'domain': domain, 'probe_dnssec_enabled': enabled, 'probe_status': status, 'dnssec_enabled': enabled, 'evidence': {'dnskey': dnskey, 'ds': ds}}


def axfr_zone(domain, target, timeout=10.0):
    dns=_dns()
    return dns.zone.from_xfr(dns.query.xfr(target, domain, lifetime=timeout, timeout=timeout))


def try_axfr(domain, ns, timeout=10.0):
    target=(ns.get('addresses') or [ns['name']])[0]
    return axfr_zone(domain, target, timeout).to_text()
