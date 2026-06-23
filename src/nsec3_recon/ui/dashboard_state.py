from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
import time

STAGES = ['preflight','dns_probe','axfr','nsec3map_detect','nsec3map_enumeration','hashcatify','scheduler','summarize']
LOW_VALUE_EVENTS = {'workspace_created','python_deps_ok','dependency_check_ok','tool_version_ok','model_assets_ok','path_check_ok','scheduler_model_assets_ok','scheduler_tool_preflight_ok','tool_preflight_ok'}

@dataclass
class DiscoveredName:
    name: str
    source: str
    method: str
    first_seen_at: str

@dataclass
class StageState:
    name: str
    status: str = 'pending'
    message: str = ''
    started_at: float | None = None
    completed_at: float | None = None
    details: dict = field(default_factory=dict)
    @property
    def duration_seconds(self):
        if not self.started_at: return None
        return (self.completed_at or time.time()) - self.started_at

@dataclass
class ArmStats:
    name: str
    run_count: int = 0; last_seen_slice: int | None = None; last_reason: str | None = None
    total_new: int = 0; last_new: int = 0; total_reward: float = 0.0; last_reward: float = 0.0
    total_runtime: float = 0.0; last_runtime: float = 0.0; last_score: float | None = None
    active: bool = False; exhausted: bool = False; last_queue_before: int | None = None; last_queue_after: int | None = None; last_phase: str | None = None
    score_history: deque = field(default_factory=lambda: deque(maxlen=30)); reward_history: deque = field(default_factory=lambda: deque(maxlen=30))
    @property
    def avg_new(self): return self.total_new / self.run_count if self.run_count else 0
    @property
    def avg_reward(self): return self.total_reward / self.run_count if self.run_count else 0
    @property
    def avg_runtime(self): return self.total_runtime / self.run_count if self.run_count else 0

def is_low_value_success_event(event) -> bool:
    return event.event in LOW_VALUE_EVENTS and event.level not in {'warning', 'error'}

class DashboardState:
    def __init__(self, domain='', workspace=None, scheduler_total_slices=None, verbose: bool = False):
        self.domain=domain; self.workspace=str(workspace or ''); self.started_at=time.time(); self.current_stage='preflight'; self.verbose=verbose
        self.completed_via=None; self.overall_status='running'; self.last_error=None
        self.warnings_count=0; self.errors_count=0; self.event_count=0
        self.stages={s: StageState(s) for s in STAGES}
        self.scheduler_started=False; self.last_completed_slice=None; self.previous_completed_slice=None; self.slice_history=deque(maxlen=100)
        self.arm_stats={}; self.recent_activity=deque(maxlen=80); self.recent_scheduler_messages=deque(maxlen=80)
        self.discovered_names_recent=deque(maxlen=200); self.discovered_names_seen=set(); self.discovered_names_count=0; self.discovered_names_by_source={}
        self.current_potfile_path=None; self.last_scheduler_stdout=None; self.last_scheduler_stderr=None; self.scheduler_runtime_started_at=None
        self.scheduler_total_slices=scheduler_total_slices
        self.completed_slices_by_key={}; self.completed_slice_order=[]; self.processed_scheduler_records={}
        self.nsec3_hash_total=0; self.nsec3_hash_cracked=0; self.latest_stdout_slice_debug=None
        self.last_scheduled_arm=None
        self.osint_status={}; self.emitted_osint_status_events=set()
    @property
    def recovered_candidates(self): return self.discovered_names_recent
    @property
    def recovered_candidate_count(self): return self.discovered_names_count
    @property
    def current_slice(self): return self.last_completed_slice
    @property
    def previous_slice(self): return self.previous_completed_slice
    @property
    def elapsed_seconds(self): return time.time()-self.started_at
    def add_activity(self, message, level='info'):
        if message: self.recent_activity.append({'ts': time.time(), 'level': level, 'message': str(message)[:180]})
    def handle_event(self, event):
        self.event_count += 1
        if event.level == 'warning': self.warnings_count += 1
        if event.level == 'error': self.errors_count += 1; self.last_error = event.message; self.overall_status='failed'
        data = getattr(event,'data',{}) or {}; stage = self._event_stage(event)
        if is_low_value_success_event(event) and not self.verbose:
            return
        if stage in self.stages:
            st=self.stages[stage]; st.message=event.message; st.details.update(data); self.current_stage=stage
            if event.event in ('started','detect_started') or event.event.endswith('_started'):
                st.status='running'; st.started_at=st.started_at or time.time()
            elif event.level == 'error' or event.event.endswith('failed'):
                st.status='failed'; st.completed_at=time.time()
            elif event.event in ('completed','detect_completed','axfr_refused') or event.event.endswith('_completed'):
                st.status='completed'; st.completed_at=time.time()
            elif event.level == 'warning': st.status='warning'
        if event.stage=='scheduler':
            if event.event=='started': self.scheduler_started=True; self.scheduler_runtime_started_at=time.time()
            if event.event=='stdout': self.last_scheduler_stdout=event.message
            if event.event=='stderr': self.last_scheduler_stderr=event.message; self.add_activity('[scheduler] stderr: '+event.message,'warning')
        if event.stage == 'hashcatify' and data.get('hash_count') is not None:
            self.nsec3_hash_total = int(data.get('hash_count') or 0)
        if event.stage == 'discovery':
            self._handle_discovery_event(event, data)
        if event.event in ('summary_written','completed') and data.get('completed_via'):
            self.completed_via=data.get('completed_via'); self.overall_status='completed'
        if self._should_add_activity(event): self.add_activity(self._format_activity(event, data), event.level)
    def _should_add_activity(self, event):
        if event.event == 'stdout': return False
        if event.level in ('warning','error'): return True
        if event.event in LOW_VALUE_EVENTS: return False
        return event.stage == 'discovery' or event.event in {'started','completed','detect_completed','detect_not_dnssec','detect_ambiguous','axfr_refused','nsec_names_extracted'} or event.event.endswith('_completed')
    def _format_activity(self, event, data):
        if event.stage == 'discovery':
            return f"[discovery] {data.get('count', data.get('name', ''))} names discovered via {data.get('source', 'unknown')}"
        if event.stage == 'hashcatify' and data.get('hash_count') is not None:
            return f"[hashcatify] hash_count={data.get('hash_count')}"
        if event.stage == 'nsec3map' and data.get('zone_type'):
            return f"[nsec3map] detected zone_type={data.get('zone_type')}"
        return f"[{event.stage}] {event.message}"
    def _event_stage(self,event):
        if event.stage=='nsec3map':
            return 'nsec3map_detect' if 'detect' in event.event else 'nsec3map_enumeration'
        return event.stage

    def update_osint_status(self, data):
        if not data or data.get('type') != 'osint_status':
            return False
        arm=data.get('arm') or 'osint/unknown'; event=data.get('event') or 'completed'; status=data.get('status') or ('running' if event == 'started' else 'unknown')
        tool=data.get('tool') or str(arm).rsplit('/', 1)[-1]
        current=self.osint_status.setdefault(tool, {'started_at': None, 'completed_at': None})
        terminal_status = current.get('status') in {'ready','exhausted','failed'}
        if event == 'started':
            key=(arm,'started')
            if terminal_status:
                return False
            if key in self.emitted_osint_status_events:
                return False
            current.update({'tool': tool, 'status': 'running', 'started_at': current.get('started_at') or datetime.now().strftime('%H:%M:%S')})
            self.emitted_osint_status_events.add(key)
            self.add_activity(self._format_osint_status_activity(data), 'info')
            return True
        current.update({k: data.get(k) for k in ('tool','status','raw_count','candidate_count','rejected_count','exit_code','reason','wordlist','raw_names') if k in data})
        if status in {'ready','exhausted','failed'}:
            current['completed_at']=datetime.now().strftime('%H:%M:%S')
        key=(arm,'completed',status,data.get('raw_count'),data.get('candidate_count'),data.get('rejected_count'),data.get('reason'),data.get('wordlist'),data.get('raw_names'),data.get('exit_code'))
        if key in self.emitted_osint_status_events:
            return False
        self.emitted_osint_status_events.add(key)
        self.add_activity(self._format_osint_status_activity(data), 'error' if status == 'failed' else 'info')
        return True

    def _format_osint_status_activity(self, data):
        arm=data.get('arm') or 'osint/unknown'; tool=data.get('tool') or str(arm).rsplit('/', 1)[-1]
        event=data.get('event') or 'completed'; status=data.get('status') or ('running' if event == 'started' else 'completed'); count=data.get('candidate_count')
        if event == 'started':
            return f"[osint] {tool} started"
        if status == 'failed':
            parts=[]
            if data.get('exit_code') is not None: parts.append(f"exit_code={data.get('exit_code')}")
            if data.get('reason'): parts.append(f"reason={data.get('reason')}")
            suffix = ': ' + ' '.join(parts) if parts else ''
            return f"[osint] {tool} failed{suffix}"
        if status == 'exhausted':
            return f"[osint] {tool} exhausted: no candidate names"
        if count is None:
            return f"[osint] {tool} completed"
        if int(count) > 0:
            return f"[osint] {tool} completed: {int(count)} candidate names ready"
        return f"[osint] {tool} completed: no candidate names"
    def _scheduler_fallback_key(self, data):
        return (data.get('slice_index') or data.get('job_id'), data.get('arm'), data.get('new'), data.get('reward'), data.get('runtime_seconds'))
    def _scheduler_record_key(self, data):
        if data.get('record_key'):
            return data.get('record_key')
        if data.get('job_id'):
            return f"job:{data.get('job_id')}"
        return self._scheduler_fallback_key(data)
    def update_scheduler_job(self, data):
        return self.update_slice(data)
    def update_slice(self, data):
        if data.get('source') is not None and data.get('source') != 'jobs_jsonl':
            return False
        record=dict(data); record.setdefault('source', 'jobs_jsonl'); key=self._scheduler_record_key(record); fallback_key=self._scheduler_fallback_key(record)
        if record.get('total_slices') is None and self.scheduler_total_slices is not None:
            record['total_slices'] = self.scheduler_total_slices
        duplicate_key = key if key in self.processed_scheduler_records else (fallback_key if fallback_key in self.processed_scheduler_records else None)
        if duplicate_key is not None:
            # Avoid double-counting when stdout fallback and jobs.jsonl report the same run.
            if record.get('source') == 'jobs_jsonl':
                existing = self.processed_scheduler_records[duplicate_key]
                existing.update(record)
                self.processed_scheduler_records[key] = existing
                self.processed_scheduler_records[fallback_key] = existing
                if self.last_completed_slice is existing:
                    self.last_completed_slice = existing
                if self.previous_completed_slice is existing:
                    self.previous_completed_slice = existing
            self._update_hash_progress(record)
            return False
        self.processed_scheduler_records[key]=record
        self.processed_scheduler_records[fallback_key]=record
        self.completed_slices_by_key[key]=record; self.completed_slice_order.append(key)
        self._recompute_last_previous(); self.slice_history.append(record); self.scheduler_started=True
        arm=record.get('arm') or 'unknown'
        self.last_scheduled_arm=arm
        for a in self.arm_stats.values(): a.active=False
        st=self.arm_stats.setdefault(arm, ArmStats(arm)); st.active=True; st.run_count+=1
        st.last_seen_slice=record.get('slice_index') or record.get('job_id'); st.last_reason=record.get('reason'); st.last_phase=record.get('phase')
        st.last_new=record.get('new') or 0; st.total_new += st.last_new
        st.last_reward=record.get('reward') or 0.0; st.total_reward += st.last_reward; st.reward_history.append(st.last_reward)
        st.last_runtime=record.get('runtime_seconds') or 0.0; st.total_runtime += st.last_runtime
        st.last_score=record.get('score_after') if record.get('score_after') is not None else record.get('score_before'); st.score_history.append(st.last_score or 0)
        st.last_queue_before=record.get('queue_before'); st.last_queue_after=record.get('queue_after')
        if record.get('exhausted') is True: st.exhausted=True
        self._update_hash_progress(record)
        return True
    def _recompute_last_previous(self):
        self.last_completed_slice = self.completed_slices_by_key[self.completed_slice_order[-1]] if self.completed_slice_order else None
        self.previous_completed_slice = self.completed_slices_by_key[self.completed_slice_order[-2]] if len(self.completed_slice_order) > 1 else None
    def _update_hash_progress(self, record):
        global_total = record.get('global_total') if record.get('global_total') is not None else record.get('total')
        if global_total is not None:
            self.nsec3_hash_cracked = max(self.nsec3_hash_cracked, int(global_total))
    @property
    def nsec3_hash_progress_percent(self):
        return (100.0 * self.nsec3_hash_cracked / self.nsec3_hash_total) if self.nsec3_hash_total else None
    def _normalize_name(self, name):
        return str(name or '').strip().lower().rstrip('.')
    def _handle_discovery_event(self, event, data):
        source=data.get('source') or 'unknown'; method=data.get('method') or 'unknown'
        if event.event == 'name_discovered':
            self.add_discovered_names([data.get('name')], source=source, method=method)
        elif event.event == 'names_discovered':
            self.add_discovered_names(data.get('names') or [], source=source, method=method, count=data.get('count'))
    def add_discovered_names(self, names, source='nsec3', method='hashcat_potfile', count=None):
        added=[]
        before_source=self.discovered_names_by_source.get(source, 0)
        for name in names or []:
            norm=self._normalize_name(name)
            if not norm or norm in self.discovered_names_seen:
                continue
            self.discovered_names_seen.add(norm)
            item=DiscoveredName(name=str(name).rstrip('.'), source=source, method=method, first_seen_at=datetime.now().strftime('%H:%M:%S'))
            self.discovered_names_recent.append(item); added.append(item)
        observed_count = int(count) if count is not None else before_source + len(added)
        self.discovered_names_by_source[source] = max(before_source + len(added), observed_count)
        self.discovered_names_count = max(len(self.discovered_names_seen), sum(self.discovered_names_by_source.values()))
        return added
    def add_recovered_candidates(self, candidates):
        return self.add_discovered_names(candidates, source='nsec3', method='hashcat_potfile')
