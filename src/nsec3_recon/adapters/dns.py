from __future__ import annotations

def _dns():
    import dns.resolver, dns.query, dns.zone
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

def dnssec_evidence(domain):
    dns=_dns(); ev={'dnskey_present':False,'ds_present':False}
    for typ,key in [('DNSKEY','dnskey_present'),('DS','ds_present')]:
        try:
            ans=dns.resolver.resolve(domain,typ,raise_on_no_answer=False)
            ev[key]=bool(ans.rrset)
        except Exception: ev[key]=False
    return {'domain':domain,'dnssec_enabled':ev['dnskey_present'] or ev['ds_present'],'evidence':ev}

def try_axfr(domain, ns):
    dns=_dns(); target=(ns.get('addresses') or [ns['name']])[0]
    z=dns.zone.from_xfr(dns.query.xfr(target, domain, lifetime=15))
    return z.to_text()
