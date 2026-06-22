from ..adapters import dns

def run(ctx):
    ctx.events.emit('axfr','started','AXFR checks started')
    attempts=[]
    for ns in ctx.state.get('nameservers',[]):
        try:
            zone=dns.try_axfr(ctx.config.domain, ns)
            (ctx.workspace.root/'axfr/zone.txt').write_text(zone)
            names=sorted({ln.split()[0].rstrip('.').lower() for ln in zone.splitlines() if ln and not ln.startswith(';')})
            (ctx.workspace.root/'axfr/names.txt').write_text('\n'.join(names)+'\n')
            res={'domain':ctx.config.domain,'supported':True,'successful_nameserver':ns['name'],'zone_file':'axfr/zone.txt','names_file':'axfr/names.txt','name_count':len(names)}
            ctx.workspace.write_json('axfr/result.json', res); ctx.state['axfr']=res
            ctx.events.emit('axfr','completed','AXFR succeeded', data=res); return res
        except Exception as e:
            attempts.append({'nameserver':ns.get('name','?'),'status':'refused','error':str(e)})
    res={'domain':ctx.config.domain,'supported':False,'successful_nameserver':None,'attempts':attempts}
    ctx.workspace.write_json('axfr/result.json', res); ctx.state['axfr']=res
    ctx.events.emit('axfr','axfr_refused','AXFR refused by all authoritative nameservers', data={'domain':ctx.config.domain,'nameservers':[n.get('name') for n in ctx.state.get('nameservers',[])]})
    return res
