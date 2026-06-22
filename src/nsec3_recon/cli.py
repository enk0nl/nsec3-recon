from __future__ import annotations
import argparse, sys
from pathlib import Path
from .config import PipelineConfig, normalize_domain
from .pipeline import Pipeline, PipelineError

def build_parser():
    p=argparse.ArgumentParser(prog='nsec3-recon', description='NSEC3 Recon')
    p.add_argument('domain', nargs='?')
    p.add_argument('--out-dir'); p.add_argument('--profile', default='demo'); p.add_argument('--no-tui', action='store_true')
    p.add_argument('--total-slices', type=int, default=150); p.add_argument('--slice-seconds', type=int, default=15); p.add_argument('--schedule', default='adaptive')
    p.add_argument('--scheduler-config'); p.add_argument('--nsec3map-bin', default='n3map'); p.add_argument('--hashcatify-bin', default='n3map-hashcatify')
    p.add_argument('--scheduler-bin', default='python3 -m nsec3_candidate_scheduler'); p.add_argument('--amass-bin', default='/home/vboxuser/go/bin/amass'); p.add_argument('--subfinder-bin', default='/home/vboxuser/go/bin/subfinder')
    p.add_argument('--assets-dir', default='assets'); p.add_argument('--dry-run', action='store_true'); p.add_argument('--verbose', action='store_true')
    return p

def main(argv=None):
    
    try:
        args=build_parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    if not args.domain: build_parser().print_help(); return 0
    try:
        cfg=PipelineConfig(domain=args.domain,out_dir=Path(args.out_dir) if args.out_dir else None,profile=args.profile,tui=(not args.no_tui and sys.stdout.isatty()),total_slices=args.total_slices,slice_seconds=args.slice_seconds,schedule=args.schedule,scheduler_config=Path(args.scheduler_config) if args.scheduler_config else None,nsec3map_bin=args.nsec3map_bin,hashcatify_bin=args.hashcatify_bin,scheduler_bin=args.scheduler_bin,amass_bin=args.amass_bin,subfinder_bin=args.subfinder_bin,assets_dir=Path(args.assets_dir),dry_run=args.dry_run,verbose=args.verbose)
        ctx=Pipeline(cfg).run(); print(f"Workspace: {ctx.workspace.root}"); return 0
    except (ValueError, PipelineError) as e:
        print(f"error: {e}", file=sys.stderr); return 2
