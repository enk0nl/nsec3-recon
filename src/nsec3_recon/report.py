from pathlib import Path
import json, time

def write_summary(ctx, completed_via, failed_stage=None, error=None):
    ax=ctx.state.get('axfr',{}); dnssec=ctx.state.get('dnssec',{}); detect=ctx.state.get('nsec3map_detect',{}); n3=ctx.state.get('nsec3map',{}); h=ctx.state.get('hashcatify',{})
    cracked=ctx.workspace.root/'reports/cracked_names.txt'
    cracked_count=sum(1 for _ in cracked.open()) if cracked.exists() else None
    artifacts={'events':'events.jsonl'}
    if ax.get('supported'): artifacts.update({'zone_file':'axfr/zone.txt','names_file':'axfr/names.txt'})
    if n3.get('zone_file'): artifacts['zone_file']=n3['zone_file']
    if h.get('hash_file'): artifacts['hash_file']=h['hash_file']
    if (ctx.workspace.root/'scheduler/run.pot').exists(): artifacts['potfile']='scheduler/run.pot'
    dnssec_probe_enabled = dnssec.get('probe_dnssec_enabled', dnssec.get('dnssec_enabled'))
    discovered = ctx.state.get('discovered_names') or {'total': 0, 'by_source': {}}
    if cracked_count:
        by_source = dict(discovered.get('by_source', {})); by_source['nsec3'] = cracked_count
        discovered = {'total': max(discovered.get('total', 0), sum(by_source.values())), 'by_source': by_source}
    obj={'domain':ctx.config.domain,'completed_via':completed_via,'axfr_supported':ax.get('supported'),'dnssec_probe_enabled':dnssec_probe_enabled,'dnssec_enabled':dnssec_probe_enabled,'nsec3map_detected_zone_type':detect.get('zone_type'),'zone_type':n3.get('zone_type') or detect.get('zone_type'),'hash_count':h.get('hash_count'),'cracked_count':cracked_count,'discovered_names':discovered,'workspace':str(ctx.workspace.root),'elapsed_seconds':round(time.time()-ctx.started_at,3),'artifacts':artifacts}
    if failed_stage: obj.update({'failed_stage':failed_stage,'error':error})
    ctx.workspace.write_json('reports/summary.json', obj)
    ctx.state['summary'] = obj
    if getattr(ctx, 'events', None):
        ctx.events.emit('summarize', 'completed', 'summary written', data=obj)
    lines=[f"# NSEC3 Recon summary",'',f"Domain: `{ctx.config.domain}`",f"Completed via: `{completed_via}`",'','## Artifacts']+[f"- {k}: `{v}`" for k,v in artifacts.items()]
    (ctx.workspace.root/'reports/summary.md').write_text('\n'.join(lines)+'\n')
    return obj
