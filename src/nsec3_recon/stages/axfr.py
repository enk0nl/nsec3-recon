from ..adapters import dns


def _zone_names(zone, domain):
    try:
        origin = zone.origin
        return sorted({str(name.derelativize(origin)).rstrip('.').lower() for name in zone.nodes.keys()})
    except Exception:
        text = zone.to_text() if hasattr(zone, 'to_text') else str(zone)
        return sorted({ln.split()[0].rstrip('.').lower() for ln in text.splitlines() if ln and not ln.startswith(';')})


def run(ctx):
    ctx.events.emit('axfr','started','AXFR checks started')
    attempts=[]
    for ns in ctx.state.get('nameservers',[]):
        targets = list(ns.get('addresses') or []) or [ns.get('name')]
        for target in targets:
            try:
                try:
                    zone=dns.axfr_zone(ctx.config.domain, target, ctx.config.axfr_timeout)
                    zone_text=zone.to_text()
                    names=_zone_names(zone, ctx.config.domain)
                except AttributeError:
                    zone_text=dns.try_axfr(ctx.config.domain, ns)
                    names=sorted({ln.split()[0].rstrip('.').lower() for ln in zone_text.splitlines() if ln and not ln.startswith(';')})
                (ctx.workspace.root/'axfr/zone.txt').write_text(zone_text, encoding='utf-8')
                (ctx.workspace.root/'axfr/names.txt').write_text('\n'.join(names)+'\n', encoding='utf-8')
                res={'domain':ctx.config.domain,'supported':True,'successful_nameserver':ns.get('name'),'successful_target':target,'zone_file':'axfr/zone.txt','names_file':'axfr/names.txt','name_count':len(names),'attempts':attempts}
                ctx.workspace.write_json('axfr/result.json', res); ctx.state['axfr']=res
                ctx.state['discovered_names']={'total':len(names),'by_source':{'axfr':len(names)}}
                ctx.events.emit('discovery','names_discovered', f'{len(names)} names discovered via AXFR', data={'source':'axfr','method':'zone_transfer','count':len(names),'names':names[-200:]})
                ctx.events.emit('axfr','completed','AXFR succeeded', data=res); return res
            except Exception as e:
                try:
                    zone_text=dns.try_axfr(ctx.config.domain, ns)
                    names=sorted({ln.split()[0].rstrip('.').lower() for ln in zone_text.splitlines() if ln and not ln.startswith(';')})
                    (ctx.workspace.root/'axfr/zone.txt').write_text(zone_text, encoding='utf-8')
                    (ctx.workspace.root/'axfr/names.txt').write_text('\n'.join(names)+'\n', encoding='utf-8')
                    res={'domain':ctx.config.domain,'supported':True,'successful_nameserver':ns.get('name'),'successful_target':target,'zone_file':'axfr/zone.txt','names_file':'axfr/names.txt','name_count':len(names),'attempts':attempts}
                    ctx.workspace.write_json('axfr/result.json', res); ctx.state['axfr']=res
                    ctx.state['discovered_names']={'total':len(names),'by_source':{'axfr':len(names)}}
                    ctx.events.emit('discovery','names_discovered', f'{len(names)} names discovered via AXFR', data={'source':'axfr','method':'zone_transfer','count':len(names),'names':names[-200:]})
                    ctx.events.emit('axfr','completed','AXFR succeeded', data=res); return res
                except Exception:
                    pass
                attempts.append({'nameserver':ns.get('name','?'),'target':target,'status':'refused','error':str(e)})
    res={'domain':ctx.config.domain,'supported':False,'successful_nameserver':None,'attempts':attempts}
    ctx.workspace.write_json('axfr/result.json', res); ctx.state['axfr']=res
    ctx.events.emit('axfr','axfr_refused','AXFR refused by all authoritative nameservers', data={'domain':ctx.config.domain,'attempts':attempts,'nameservers':[n.get('name') for n in ctx.state.get('nameservers',[])]})
    return res
