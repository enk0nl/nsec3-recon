from __future__ import annotations
import argparse, sys
from pathlib import Path
from .config import PipelineConfig
from .pipeline import Pipeline, PipelineError

def build_parser():
    p = argparse.ArgumentParser(prog="nsec3-recon", description="NSEC3 Recon")
    p.add_argument("domain", nargs="?")
    p.add_argument("--out-dir")
    p.add_argument("--dashboard", choices=("auto", "rich", "plain", "off"), default="auto", help="live UI mode (default: auto)")
    p.add_argument("--dashboard-refresh-rate", type=float, default=2.0, help="Rich dashboard refreshes per second (default: 2.0)")
    p.add_argument("--total-slices", type=int, default=150)
    p.add_argument("--slice-seconds", type=int, default=15)
    p.add_argument("--schedule", default="adaptive")
    p.add_argument("--scheduler-config")
    p.add_argument("--config-template")
    p.add_argument("--nsec3map-source-dir", default="deps/src/nsec3map")
    p.add_argument("--nsec3map-python", default=sys.executable)
    p.add_argument("--scheduler-bin", default="python3 -m nsec3_candidate_scheduler")
    p.add_argument("--hashcat-bin", default="hashcat")
    p.add_argument("--amass-bin", default="~/go/bin/amass")
    p.add_argument("--subfinder-bin", default="~/go/bin/subfinder")
    p.add_argument("--assets-dir", default="assets")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p

def main(argv=None):
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    if not args.domain:
        build_parser().print_help()
        return 0
    try:
        cfg = PipelineConfig(
            domain=args.domain,
            out_dir=Path(args.out_dir) if args.out_dir else None,
            dashboard=args.dashboard,
            dashboard_refresh_rate=args.dashboard_refresh_rate,
            total_slices=args.total_slices,
            slice_seconds=args.slice_seconds,
            schedule=args.schedule,
            scheduler_config=Path(args.scheduler_config) if args.scheduler_config else None,
            config_template=Path(args.config_template) if args.config_template else None,
            nsec3map_source_dir=Path(args.nsec3map_source_dir),
            nsec3map_python=args.nsec3map_python,
            scheduler_bin=args.scheduler_bin,
            hashcat_bin=args.hashcat_bin,
            amass_bin=args.amass_bin,
            subfinder_bin=args.subfinder_bin,
            assets_dir=Path(args.assets_dir),
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        ctx = Pipeline(cfg).run()
        summary = ctx.state.get('summary', {})
        completed = summary.get('completed_via')
        if completed:
            print(f"Completed via: {completed}")
            if completed == 'not_dnssec':
                print('Reason: nsec3map detect-only did not report NSEC or NSEC3')
        print(f"Summary: {ctx.workspace.root/'reports/summary.json'}")
        recovered = getattr(getattr(ctx, 'dashboard_controller', None), 'state', None)
        if recovered is not None:
            print(f"Recovered candidates: {recovered.recovered_candidate_count}")
        return 0
    except (ValueError, PipelineError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
