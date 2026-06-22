from __future__ import annotations

def _dns():
    import dns.resolver, dns.query, dns.zone, dns.flags, dns.exception
    return dns

def authoritative_nameservers(domain):
    dns=_dns(); out=[]
    for rr in dns.resolver.resolve(domain,'NS'):
        name=str(rr.target).rstrip('.')
        addrs=[]
        for typ in ('A','AAAA'):
            try: addrs += [str(a) for a in dns.resolver.resolve(name,typ)]
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

def dnssec_evidence(domain):
    dns=_dns()
    resolver=dns.resolver.Resolver()
    try:
        resolver.use_edns(edns=0, ednsflags=dns.flags.DO)
    except Exception:
        pass
    dnskey = _query_evidence(resolver, dns, domain, 'DNSKEY')
    ds = _query_evidence(resolver, dns, domain, 'DS')
    enabled = dnskey['present'] or ds['present']
    if enabled:
        status = 'enabled'
    elif dnskey['status'] == 'error' or ds['status'] == 'error':
        status = 'unknown'
    else:
        status = 'not_detected'
    return {
        'domain': domain,
        'probe_dnssec_enabled': enabled,
        'probe_status': status,
        'dnssec_enabled': enabled,
        'evidence': {'dnskey': dnskey, 'ds': ds},
    }

def try_axfr(domain, ns):
    dns=_dns(); target=(ns.get('addresses') or [ns['name']])[0]
    z=dns.zone.from_xfr(dns.query.xfr(target, domain, lifetime=15))
    return z.to_text()
