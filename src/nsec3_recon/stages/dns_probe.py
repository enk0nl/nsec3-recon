from ..adapters import dns

def run(ctx):
    ctx.events.emit('dns_probe','started','DNS probe started')
    ns=dns.authoritative_nameservers(ctx.config.domain)
    sec=dns.dnssec_evidence(ctx.config.domain)
    ctx.state['nameservers']=ns; ctx.state['dnssec']=sec
    ctx.workspace.write_json('probe/nameservers.json', {'domain':ctx.config.domain,'nameservers':ns})
    ctx.workspace.write_json('probe/dnssec.json', sec)
    ctx.events.emit('dns_probe','completed','DNS probe completed', data={'dnssec_probe_enabled':sec.get('probe_dnssec_enabled'), 'probe_status': sec.get('probe_status')})
    return sec
