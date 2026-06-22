from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path
import time

STAGES = ['preflight','dns_probe','axfr','nsec3map_detect','nsec3map_enumeration','hashcatify','scheduler','summarize']
_STAGE_MAP = {'nsec3map': 'nsec3map_detect'}

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
    active: bool = False; last_queue_before: int | None = None; last_queue_after: int | None = None
    score_history: deque = field(default_factory=lambda: deque(maxlen=30)); reward_history: deque = field(default_factory=lambda: deque(maxlen=30))
    @property
    def avg_new(self): return self.total_new / self.run_count if self.run_count else 0
    @property
    def avg_reward(self): return self.total_reward / self.run_count if self.run_count else 0
    @property
    def avg_runtime(self): return self.total_runtime / self.run_count if self.run_count else 0

class DashboardState:
    def __init__(self, domain='', workspace=None):
        self.domain=domain; self.workspace=str(workspace or ''); self.started_at=time.time(); self.current_stage='preflight'
        self.completed_via=None; self.overall_status='running'; self.last_error=None
        self.warnings_count=0; self.errors_count=0; self.event_count=0
        self.stages={s: StageState(s) for s in STAGES}
        self.scheduler_started=False; self.current_slice=None; self.previous_slice=None; self.slice_history=deque(maxlen=100)
        self.arm_stats={}; self.recent_activity=deque(maxlen=80); self.recent_scheduler_messages=deque(maxlen=80)
        self.recovered_candidates=deque(maxlen=200); self._candidate_seen=set(); self.recovered_candidate_count=0
        self.current_potfile_path=None; self.last_scheduler_stdout=None; self.last_scheduler_stderr=None; self.scheduler_runtime_started_at=None
    @property
    def elapsed_seconds(self): return time.time()-self.started_at
    def add_activity(self, message, level='info'):
        if message: self.recent_activity.append({'ts': time.time(), 'level': level, 'message': str(message)[:240]})
    def handle_event(self, event):
        self.event_count += 1
        if event.level == 'warning': self.warnings_count += 1
        if event.level == 'error': self.errors_count += 1; self.last_error = event.message; self.overall_status='failed'
        data = getattr(event,'data',{}) or {}; stage = self._event_stage(event)
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
            if event.event=='stderr': self.last_scheduler_stderr=event.message; self.add_activity('scheduler stderr: '+event.message,'warning')
        if event.event in ('summary_written','completed') and data.get('completed_via'):
            self.completed_via=data.get('completed_via'); self.overall_status='completed'
        if event.level in ('warning','error') or event.event not in ('stdout',): self.add_activity(f"{event.stage}: {event.message}", event.level)
    def _event_stage(self,event):
        if event.stage=='nsec3map':
            return 'nsec3map_detect' if 'detect' in event.event else 'nsec3map_enumeration'
        return event.stage
    def update_slice(self, data):
        self.previous_slice=self.current_slice; self.current_slice=dict(data); self.slice_history.append(dict(data)); self.scheduler_started=True
        arm=data.get('arm') or 'unknown'
        for a in self.arm_stats.values(): a.active=False
        st=self.arm_stats.setdefault(arm, ArmStats(arm)); st.active=True; st.run_count+=1
        st.last_seen_slice=data.get('slice_index'); st.last_reason=data.get('reason')
        st.last_new=data.get('new') or 0; st.total_new += st.last_new
        st.last_reward=data.get('reward') or 0.0; st.total_reward += st.last_reward; st.reward_history.append(st.last_reward)
        st.last_runtime=data.get('runtime_seconds') or 0.0; st.total_runtime += st.last_runtime
        st.last_score=data.get('score_after') if data.get('score_after') is not None else data.get('score_before'); st.score_history.append(st.last_score or 0)
        st.last_queue_before=data.get('queue_before'); st.last_queue_after=data.get('queue_after')
    def add_recovered_candidates(self, candidates):
        added=[]
        for c in candidates or []:
            if c and c not in self._candidate_seen:
                self._candidate_seen.add(c); self.recovered_candidate_count+=1; item={'ts':time.time(),'candidate':c}; self.recovered_candidates.appendleft(item); added.append(c)
        return added
