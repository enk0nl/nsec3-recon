import json
from pathlib import Path

from nsec3_recon.adapters.scheduler import render_scheduler_config
from nsec3_recon.config import PipelineConfig
from nsec3_recon.pipeline import PipelineContext
from nsec3_recon.workspace import Workspace
from nsec3_recon.events import EventSink
from nsec3_recon.report import write_summary
from nsec3_recon.ui.dashboard_state import DashboardState
from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record, normalize_scheduler_status_record


def test_scheduler_config_top_level_hashcat_defaults(tmp_path):
    cfg = render_scheduler_config('example.nl', 'assets', tmp_path/'scheduler.json')
    assert cfg['hashcat']['optimized_kernels'] is True
    assert cfg['hashcat']['optimized_kernel_failover'] is True


def test_scheduler_config_top_level_hashcat_disabled_values(tmp_path):
    cfg = render_scheduler_config('example.nl', 'assets', tmp_path/'scheduler.json', hashcat_optimized_kernels=False, hashcat_optimized_kernel_failover=False)
    assert cfg['hashcat']['optimized_kernels'] is False
    assert cfg['hashcat']['optimized_kernel_failover'] is False
    for arm in cfg['arms']:
        if 'hashcat' in arm:
            assert arm['hashcat']['optimized_kernels'] is False
            assert 'optimized_kernel_failover' not in arm['hashcat']


def test_scheduler_command_optimized_kernel_disable_flags(tmp_path):
    cmd = PipelineConfig('example.nl', hashcat_optimized_kernels=False, hashcat_optimized_kernel_failover=False).scheduler_command(tmp_path, tmp_path/'h', tmp_path/'c')
    assert '--no-optimized-kernels' in cmd
    assert '--no-optimized-kernel-failover' in cmd


def test_scheduler_command_default_omits_optimized_kernel_disable_flags(tmp_path):
    cmd = PipelineConfig('example.nl').scheduler_command(tmp_path, tmp_path/'h', tmp_path/'c')
    assert '--no-optimized-kernels' not in cmd
    assert '--no-optimized-kernel-failover' not in cmd


def test_dashboard_failover_activity_and_scoring_rules():
    s = DashboardState('example.nl', '/tmp/ws')
    failed = {'job_id': 24, 'arm': 'dict/a', 'new': 0, 'valid_work': False, 'scored': False, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': True, 'optimized_kernel_failover_enabled': True}
    assert normalize_scheduler_record(failed) is None
    status = normalize_scheduler_status_record(failed)
    s.update_arm_status(status.data)
    s.update_arm_status(status.data)
    assert 'dict/a' in s.arm_stats
    assert s.arm_stats['dict/a'].run_count == 0
    messages = [a['message'] for a in s.recent_activity]
    assert messages.count('[hashcat] optimized kernels failed; retrying with unoptimized kernels') == 1
    retry = {'job_id': 25, 'arm': 'dict/a', 'new': 2, 'valid_work': True, 'scored': True, 'retry_of_job_id': 24, 'retry_reason': 'optimized_kernel_failure'}
    s.update_slice(normalize_scheduler_record(retry).data)
    assert s.arm_stats['dict/a'].run_count == 1
    assert s.arm_stats['dict/a'].total_new == 2


def test_dashboard_failover_disabled_activity():
    s = DashboardState('example.nl', '/tmp/ws')
    record = {'job_id': 24, 'arm': 'dict/a', 'valid_work': False, 'scored': False, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': False, 'optimized_kernel_failover_enabled': False}
    s.update_arm_status(normalize_scheduler_status_record(record).data)
    assert any('failover disabled, continuing optimized' in a['message'] for a in s.recent_activity)


def test_summary_records_requested_and_observed_failover(tmp_path):
    ws = Workspace.create('example.nl', tmp_path/'r')
    (ws.root/'scheduler').mkdir(exist_ok=True)
    jobs = [
        {'job_id': 24, 'hashcat_optimized_kernels': True, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': True},
        {'job_id': 25, 'hashcat_optimized_kernels': False, 'retry_of_job_id': 24, 'retry_reason': 'optimized_kernel_failure'},
    ]
    (ws.root/'scheduler/jobs.jsonl').write_text('\n'.join(json.dumps(j) for j in jobs)+'\n')
    ctx = PipelineContext(PipelineConfig('example.nl'), ws, EventSink(ws.root/'events.jsonl'))
    data = write_summary(ctx, 'nsec3_scheduler')
    assert data['requested_hashcat_optimized_kernels'] is True
    assert data['requested_hashcat_optimized_kernel_failover'] is True
    assert data['observed_hashcat_optimized_kernels'] is False
    assert data['hashcat_optimized_kernel_failover'] is True
    assert data['hashcat_optimized_kernel_failover_job_id'] == 24


def test_summary_records_failover_disabled_failures(tmp_path):
    ws = Workspace.create('example.nl', tmp_path/'r')
    (ws.root/'scheduler').mkdir(exist_ok=True)
    (ws.root/'scheduler/jobs.jsonl').write_text(json.dumps({'job_id': 1, 'hashcat_optimized_kernels': True, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': False, 'optimized_kernel_failover_enabled': False})+'\n')
    ctx = PipelineContext(PipelineConfig('example.nl', hashcat_optimized_kernel_failover=False), ws, EventSink(ws.root/'events.jsonl'))
    data = write_summary(ctx, 'nsec3_scheduler')
    assert data['requested_hashcat_optimized_kernel_failover'] is False
    assert data['hashcat_optimized_kernel_failover'] is False
    assert data['hashcat_optimized_kernel_failover_disabled_failures'] == 1
