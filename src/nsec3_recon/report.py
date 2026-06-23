from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path


def _utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _sha256(path: Path, max_bytes: int = 50_000_000) -> str | None:
    if path.stat().st_size > max_bytes:
        return None
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_artifacts_manifest(ctx, roles: dict[str, str] | None = None):
    roles = roles or {}
    items = []
    for path in sorted(ctx.workspace.root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(ctx.workspace.root).as_posix()
        st = path.stat()
        items.append({
            'path': rel,
            'role': roles.get(rel, 'artifact'),
            'size': st.st_size,
            'sha256': _sha256(path),
            'created_at': datetime.fromtimestamp(st.st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        })
    p = ctx.workspace.write_json('reports/artifacts.json', {'schema_version': 1, 'artifacts': items})
    return p

def _load_scheduler_jobs(root: Path) -> list[dict]:
    path = root / 'scheduler/jobs.jsonl'
    if not path.exists():
        return []
    jobs = []
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            jobs.append(obj)
    return jobs

def _optimized_kernel_summary(ctx) -> dict:
    jobs = _load_scheduler_jobs(ctx.workspace.root)
    observed = [j.get('hashcat_optimized_kernels') for j in jobs if 'hashcat_optimized_kernels' in j]
    failover_records = [j for j in jobs if j.get('retry_reason') == 'optimized_kernel_failure' and j.get('retry_scheduled') is True]
    retry_records = [j for j in jobs if j.get('retry_reason') == 'optimized_kernel_failure' and j.get('retry_of_job_id') is not None]
    failover = bool(failover_records or retry_records)
    trigger = failover_records[0].get('job_id') if failover_records else (retry_records[0].get('retry_of_job_id') if retry_records else None)
    disabled_failures = sum(1 for j in jobs if j.get('retry_reason') == 'optimized_kernel_failure' and j.get('optimized_kernel_failover_enabled') is False and j.get('retry_scheduled') is False)
    observed_state = None
    if observed:
        if failover and any(v is False for v in observed):
            observed_state = False
        elif all(v is True for v in observed):
            observed_state = True
        elif all(v is False for v in observed):
            observed_state = False
        else:
            observed_state = bool(observed[-1])
    return {
        'requested_hashcat_optimized_kernels': bool(ctx.config.hashcat_optimized_kernels),
        'requested_hashcat_optimized_kernel_failover': bool(ctx.config.hashcat_optimized_kernel_failover),
        'observed_hashcat_optimized_kernels': observed_state,
        'hashcat_optimized_kernel_failover': failover,
        'hashcat_optimized_kernel_failover_job_id': trigger,
        'hashcat_optimized_kernel_failover_disabled_failures': disabled_failures,
    }

def _optimized_kernel_summary_line(meta: dict) -> str:
    if meta.get('requested_hashcat_optimized_kernels') is False:
        return 'Hashcat optimized kernels: disabled from start'
    if meta.get('hashcat_optimized_kernel_failover'):
        return f"Hashcat optimized kernels: requested enabled, automatically disabled after job {meta.get('hashcat_optimized_kernel_failover_job_id')}"
    disabled = meta.get('hashcat_optimized_kernel_failover_disabled_failures') or 0
    if meta.get('requested_hashcat_optimized_kernel_failover') is False:
        return f"Hashcat optimized kernels: requested enabled; automatic failover disabled; {disabled} optimized-kernel failures observed"
    return 'Hashcat optimized kernels: requested enabled; automatic failover enabled'


def write_summary(ctx, completed_via, failed_stage=None, error=None):
    ax=ctx.state.get('axfr',{}); dnssec=ctx.state.get('dnssec',{}); detect=ctx.state.get('nsec3map_detect',{}); n3=ctx.state.get('nsec3map',{}); h=ctx.state.get('hashcatify',{})
    cracked_count = ctx.state.get('cracked_count')
    cracked = ctx.workspace.root/'reports/cracked_names.txt'
    if cracked_count is None and cracked.exists():
        cracked_count=sum(1 for line in cracked.read_text(encoding='utf-8', errors='ignore').splitlines() if line.strip())
    discovered_state = ctx.state.get('discovered_names')
    if isinstance(discovered_state, dict):
        discovered_count = ctx.state.get('discovered_names_count', discovered_state.get('total'))
        discovered_names = []
        discovered_by_source = ctx.state.get('discovered_names_by_source') or discovered_state.get('by_source', {})
    else:
        discovered_count = ctx.state.get('discovered_names_count')
        discovered_names = discovered_state or []
        discovered_by_source = ctx.state.get('discovered_names_by_source') or ({'nsec3': discovered_count} if discovered_count is not None else {})
    artifacts={'events':'events.jsonl'}
    for rel, key in [('reports/cracked_names.txt','cracked_names'),('reports/discovered_names.txt','discovered_names'),('reports/discovered_names.json','discovered_names_json'),('config/dependency_manifest.json','dependency_manifest')]:
        if (ctx.workspace.root/rel).exists(): artifacts[key]=rel
    if ax.get('supported'): artifacts.update({'zone_file':'axfr/zone.txt','names_file':'axfr/names.txt'})
    if n3.get('zone_file'): artifacts['zone_file']=n3['zone_file']
    if h.get('hash_file'): artifacts['hash_file']=h['hash_file']
    if (ctx.workspace.root/'scheduler/run.pot').exists(): artifacts['potfile']='scheduler/run.pot'
    roles = {v: k for k, v in artifacts.items()}
    artifact_manifest = write_artifacts_manifest(ctx, roles)
    artifacts['artifact_manifest'] = artifact_manifest.relative_to(ctx.workspace.root).as_posix()
    dnssec_probe_enabled = dnssec.get('probe_dnssec_enabled', dnssec.get('dnssec_enabled'))
    completed_at = _utc()
    run_meta = getattr(ctx.workspace, 'run_metadata', {}) or {}
    kernel_meta = _optimized_kernel_summary(ctx)
    obj={
        'schema_version': 1,
        'run_id': run_meta.get('run_id'),
        'domain':ctx.config.domain,
        'started_at': run_meta.get('created_at'),
        'completed_at': completed_at,
        'completed_via':completed_via,
        'axfr_supported':ax.get('supported'),
        'dnssec_probe_enabled':dnssec_probe_enabled,
        'dnssec_enabled':dnssec_probe_enabled,
        'nsec3map_detected_zone_type':detect.get('zone_type'),
        'nsec3map_hashlimit': ctx.config.nsec3map_hashlimit,
        'zone_type':n3.get('zone_type') or detect.get('zone_type'),
        'hash_count':h.get('hash_count'),
        'cracked_count':cracked_count,
        'discovered_names_count': discovered_count if discovered_count is not None else len(discovered_names),
        'discovered_names_by_source': discovered_by_source,
        'discovered_names': {'total': discovered_count if discovered_count is not None else len(discovered_names), 'by_source': discovered_by_source},
        'scheduler_slices_completed': ctx.state.get('scheduler_slices_completed'),
        'scheduler_total_slices': ctx.config.total_slices,
        'top_arms_by_total': ctx.state.get('top_arms_by_total', []),
        'workspace':str(ctx.workspace.root),
        'elapsed_seconds':round(time.time()-ctx.started_at,3),
        'artifacts':artifacts,
        'dependency_manifest': artifacts.get('dependency_manifest'),
        **kernel_meta,
    }
    if failed_stage: obj.update({'failed_stage':failed_stage,'error':error})
    ctx.workspace.write_json('reports/summary.json', obj)
    ctx.state['summary'] = obj
    if getattr(ctx, 'events', None):
        ctx.events.emit('summarize', 'completed', 'summary written', data=obj)
    lines=["# NSEC3 Recon summary",'',f"Domain: `{ctx.config.domain}`",f"Run ID: `{obj.get('run_id')}`",f"Completed via: `{completed_via}`",f"Hash count: `{obj.get('hash_count')}`",f"Cracked count: `{obj.get('cracked_count')}`",f"Discovered names: `{obj.get('discovered_names_count')}`",f"nsec3map hash limit: `{obj.get('nsec3map_hashlimit')}`",_optimized_kernel_summary_line(kernel_meta),'',"## Artifacts"]+[f"- {k}: `{v}`" for k,v in artifacts.items()]
    (ctx.workspace.root/'reports/summary.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return obj
