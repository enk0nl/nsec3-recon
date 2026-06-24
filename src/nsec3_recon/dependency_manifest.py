from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .adapters.tools import AMASS_MIN, HASHCAT_MIN, SUBFINDER_MIN

GIT_DEPS = {
    'nsec3map': ('https://github.com/enk0nl/nsec3map', 'NSEC3MAP_REF', '5af04b9c900b8f0f1a2113a22f5b34e67e637c80', 'deps/src/nsec3map'),
    'nsec3-candidate-scheduler': ('https://github.com/enk0nl/nsec3-candidate-scheduler', 'SCHEDULER_REF', 'cde74dbbccc641161846a9ccabf81551c3d586c1', 'deps/src/nsec3-candidate-scheduler'),
    'pcfg-subdomain-generator': ('https://github.com/enk0nl/pcfg-subdomain-generator', 'PCFG_REF', '171f89e85206cb22e89c3803c13f6a320d538e8b', 'deps/src/pcfg-subdomain-generator'),
    'SecLists': ('https://github.com/danielmiessler/SecLists', 'SECLISTS_REF', '198047f1e22251e3b88b98b10e8bd15283e8a1e9', 'deps/src/SecLists'),
    'opentaal-wordlist': ('https://github.com/OpenTaal/opentaal-wordlist', 'OPENTAAL_REF', 'b250510dda431785f962019167d1415198ff3905', 'deps/src/opentaal-wordlist'),
    'dutch-dns-wordlists': ('https://github.com/enk0nl/dutch-dns-wordlists', 'DUTCH_DNS_WORDLISTS_REF', '87403dff13f2a9da53084c88412a6e19280003ec', 'deps/src/dutch-dns-wordlists'),
}


def _run(cmd):
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=10).stdout.strip()
    except Exception:
        return ''


def write_dependency_manifest(ctx):
    deps=[]
    for name, (remote, env_name, requested, rel) in GIT_DEPS.items():
        path=Path(rel).resolve()
        resolved=_run(['git','-C',str(path),'rev-parse','HEAD']) if (path/'.git').exists() else None
        requested_ref = os.environ.get(env_name, requested)
        item = {'name': name, 'type': 'git', 'remote_url': remote, 'requested_ref': requested_ref, 'resolved_commit': resolved, 'local_path': str(path)}
        if name == 'nsec3-candidate-scheduler':
            help_output = _run(['python3', '-m', 'nsec3_candidate_scheduler', 'run', '--help'])
            item['optimized_kernel_option_support'] = {
                'no_optimized_kernels': '--no-optimized-kernels' in help_output,
                'optimized_kernel_failover': '--optimized-kernel-failover' in help_output,
                'no_optimized_kernel_failover': '--no-optimized-kernel-failover' in help_output,
            }
        deps.append(item)
    bins=[('hashcat', ctx.config.hashcat_bin, HASHCAT_MIN, ['--version']),('amass', ctx.config.amass_bin, AMASS_MIN, ['-version']),('subfinder', ctx.config.subfinder_bin, SUBFINDER_MIN, ['-version'])]
    for name, cmd, minimum, args in bins:
        exe=str(cmd).split()[0]
        deps.append({'name': name, 'type': 'binary', 'local_path': cmd, 'minimum_required_version': minimum, 'detected_version_output': _run([exe, *args])})
    return ctx.workspace.write_json('config/dependency_manifest.json', {'schema_version': 1, 'dependencies': deps})
