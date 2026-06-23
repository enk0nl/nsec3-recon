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
    assert messages.count('[scheduler] optimized kernels failed; retrying unoptimized') == 1
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


def test_recent_activity_shows_optimized_kernel_failover():
    s = DashboardState('example.nl', '/tmp/ws')
    record = {'job_id': 24, 'arm': 'dict/nsec_data', 'hashcat_optimized_kernels': True, 'optimized_kernel_failover_enabled': True, 'valid_work': False, 'scored': False, 'retryable': True, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': True}
    s.update_arm_status(normalize_scheduler_status_record(record).data)
    assert '[scheduler] optimized kernels failed; retrying unoptimized' in [a['message'] for a in s.recent_activity]


def test_recent_activity_shows_all_hashes_token_length_failover():
    s = DashboardState('example.nl', '/tmp/ws')
    record = {'job_id': 24, 'arm': 'bruteforce/rfc1035_len2_5', 'hashcat_optimized_kernels': True, 'optimized_kernel_failover_enabled': True, 'valid_work': False, 'scored': False, 'retryable': True, 'retry_reason': 'optimized_kernel_all_hashes_token_length', 'retry_scheduled': True, 'hashcat_parse_error_count': 22, 'hashcat_parse_error_total': 22}
    s.update_arm_status(normalize_scheduler_status_record(record).data)
    assert '[scheduler] optimized kernels failed on all hashes; retrying unoptimized' in [a['message'] for a in s.recent_activity]


def test_recent_activity_shows_failover_disabled():
    s = DashboardState('example.nl', '/tmp/ws')
    record = {'job_id': 24, 'arm': 'dict/nsec_data', 'hashcat_optimized_kernels': True, 'optimized_kernel_failover_enabled': False, 'valid_work': False, 'scored': False, 'retryable': False, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': False, 'availability_reason': 'optimized_kernel_failure_no_failover'}
    s.update_arm_status(normalize_scheduler_status_record(record).data)
    assert '[scheduler] optimized kernels failed; failover disabled, continuing optimized' in [a['message'] for a in s.recent_activity]


def test_recent_activity_shows_all_hashes_failover_disabled():
    s = DashboardState('example.nl', '/tmp/ws')
    record = {'job_id': 24, 'arm': 'bruteforce/rfc1035_len2_5', 'hashcat_optimized_kernels': True, 'optimized_kernel_failover_enabled': False, 'valid_work': False, 'scored': False, 'retryable': False, 'retry_reason': 'optimized_kernel_all_hashes_token_length', 'retry_scheduled': False}
    s.update_arm_status(normalize_scheduler_status_record(record).data)
    assert '[scheduler] optimized kernels failed; failover disabled, continuing optimized' in [a['message'] for a in s.recent_activity]


def test_failover_activity_is_deduplicated():
    s = DashboardState('example.nl', '/tmp/ws')
    record = {'job_id': 24, 'arm': 'dict/nsec_data', 'optimized_kernel_failover_enabled': True, 'valid_work': False, 'scored': False, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': True}
    status = normalize_scheduler_status_record(record).data
    s.update_arm_status(status)
    s.update_arm_status(status)
    messages = [a['message'] for a in s.recent_activity]
    assert messages.count('[scheduler] optimized kernels failed; retrying unoptimized') == 1


def test_failover_activity_uses_structured_record_not_hint():
    s = DashboardState('example.nl', '/tmp/ws')
    long_hint = 'This is a very long hashcat optimized kernel hint that should not be rendered in Recent activity.' * 20
    record = {'job_id': 24, 'arm': 'dict/nsec_data', 'optimized_kernel_failover_enabled': True, 'valid_work': False, 'scored': False, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': True, 'hashcat_optimized_kernel_hint': long_hint}
    s.update_arm_status(normalize_scheduler_status_record(record).data)
    text = '\n'.join(a['message'] for a in s.recent_activity)
    assert '[scheduler] optimized kernels failed; retrying unoptimized' in text
    assert long_hint not in text


def test_failed_optimized_kernel_record_does_not_update_arm_stats():
    s = DashboardState('example.nl', '/tmp/ws')
    record = {'source': 'jobs_jsonl', 'job_id': 24, 'arm': 'dict/nsec_data', 'new': 7, 'reward': 3.5, 'score_after': 0.8, 'runtime_seconds': 12.0, 'valid_work': False, 'scored': False, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': True, 'optimized_kernel_failover_enabled': True}
    assert s.update_slice(record) is False
    stats = s.arm_stats.get('dict/nsec_data')
    assert stats is None or (stats.run_count, stats.total_new, stats.last_new, stats.last_reward, stats.last_score) == (0, 0, 0, 0.0, None)


def test_retry_job_updates_arm_stats_normally():
    s = DashboardState('example.nl', '/tmp/ws')
    failed = {'source': 'jobs_jsonl', 'job_id': 24, 'arm': 'dict/nsec_data', 'new': 7, 'valid_work': False, 'scored': False, 'retry_reason': 'optimized_kernel_failure', 'retry_scheduled': True, 'optimized_kernel_failover_enabled': True}
    retry = {'job_id': 25, 'arm': 'dict/nsec_data', 'hashcat_optimized_kernels': False, 'retry_of_job_id': 24, 'valid_work': True, 'scored': True, 'new': 2, 'reward': 1.25, 'score_after': 0.4, 'runtime_seconds': 9.0}
    assert s.update_slice(failed) is False
    s.update_slice(normalize_scheduler_record(retry).data)
    stats = s.arm_stats['dict/nsec_data']
    assert stats.run_count == 1
    assert stats.total_new == 2
    assert stats.last_new == 2
    assert stats.last_reward == 1.25
    assert stats.last_score == 0.4
