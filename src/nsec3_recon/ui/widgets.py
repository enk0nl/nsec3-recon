from __future__ import annotations
from .theme import STATUS_GLYPHS, STATUS_STYLES

ARM_ROW_LIMIT = 8
RECOVERED_ROW_LIMIT = 24
ACTIVITY_ROW_LIMIT = 10

def fmt_time(sec):
    sec=int(sec or 0); return f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"

def shorten_middle(value: str, max_len: int = 28) -> str:
    value = value or ''
    if len(value) <= max_len: return value
    keep = max_len - 1
    left = max(8, keep // 2)
    right = keep - left
    return value[:left] + '…' + value[-right:]

def _slice_lines(s):
    if not s: return ['waiting for completed scheduler slice…']
    lines=[f"slice {s.get('slice_index','?')}/{s.get('total_slices','?')}  policy={s.get('schedule_name','?')}", f"arm={s.get('arm','?')}  reason={s.get('reason','-')}"]
    lines.append(f"new={s.get('new','-')}  total={s.get('total','-')}  reward={_fmt_float(s.get('reward'))}  runtime={_fmt_runtime(s.get('runtime_seconds'))}")
    if s.get('score_before') is not None: lines.append(f"score {_fmt_float(s.get('score_before'))} → {_fmt_float(s.get('score_after'))}")
    if s.get('queue_before') is not None: lines.append(f"queue {s.get('queue_before')} → {s.get('queue_after')}")
    for name in ('skip','gate_queue','cooldown'):
        a=s.get(f'{name}_before') if name=='skip' else s.get(f'{name}_current')
        b=s.get(f'{name}_after') if name=='skip' else s.get(f'{name}_required')
        if a is not None: lines.append(f"{name} {a} → {b}")
    if s.get('progress'): lines.append(f"progress {s.get('progress')}")
    return lines

def _fmt_float(value, ndigits=2):
    return '-' if value is None else f"{float(value):.{ndigits}f}"

def _fmt_runtime(value):
    return '-' if value is None else f"{float(value):.1f}s"

def _build_arm_panel(state):
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    arms = Table(expand=True, show_edge=False, box=None, pad_edge=False)
    arms.add_column('Arm', overflow='ellipsis', ratio=3, no_wrap=True)
    for col in ('Runs','New','Last','Avg R','Last R','Avg t','Seen'):
        arms.add_column(col, justify='right', no_wrap=True)
    sorted_arms=sorted(state.arm_stats.values(), key=lambda a:(not a.active, -a.total_new, -a.avg_reward, -a.run_count))
    for a in sorted_arms[:ARM_ROW_LIMIT]:
        arm_name = shorten_middle(a.name, 30)
        if a.active: arm_name = '▶ ' + arm_name
        arms.add_row(arm_name, str(a.run_count), str(a.total_new), str(a.last_new), _fmt_float(a.avg_reward), _fmt_float(a.last_reward), _fmt_runtime(a.avg_runtime), str(a.last_seen_slice or '-'))
    if not sorted_arms:
        arms.add_row('waiting for scheduler slices', '', '', '', '', '', '', '')
    hidden=max(0, len(sorted_arms)-ARM_ROW_LIMIT)
    footer = f"+{hidden} more arms" if hidden else "sorted by active, new discoveries, reward"
    return Panel(arms, title='Arm statistics', subtitle=footer, border_style='green')

def _build_recovered_panel(state):
    from rich.panel import Panel
    from rich.table import Table
    rec = Table.grid(expand=True)
    rec.add_column('Time', width=8, no_wrap=True, style='cyan')
    rec.add_column('Candidate', overflow='ellipsis', ratio=1, style='bold white')
    rows=list(state.recovered_candidates)[-RECOVERED_ROW_LIMIT:]
    if rows:
        for item in rows:
            rec.add_row(item.get('timestamp','--:--:--'), item.get('candidate',''))
    else:
        msg='potfile not detected yet' if not state.current_potfile_path else 'waiting for recovered candidates…'
        rec.add_row('', msg)
    source = f"source: {state.current_potfile_path.split('/')[-1]}" if state.current_potfile_path else 'potfile not detected yet'
    return Panel(rec, title='Recovered candidates', subtitle=f"total={state.recovered_candidate_count}  {source}", border_style='bright_yellow')

def _build_activity_panel(state):
    from rich.panel import Panel
    from rich.text import Text
    lines=[]
    style_by_level={'warning':'yellow','error':'red','info':'white','debug':'dim'}
    for a in list(state.recent_activity)[-ACTIVITY_ROW_LIMIT:]:
        lines.append(Text(str(a['message']), style=style_by_level.get(a.get('level'), 'white')))
    body=Text('\n').join(lines) if lines else Text('no recent activity', style='dim')
    return Panel(body, title='Recent activity', border_style='blue')

def build_dashboard(state):
    try:
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except Exception as e:
        raise RuntimeError('Rich is required for dashboard rendering') from e
    header=Panel(Text.assemble(('NSEC3 RECON','bold bright_cyan'),('  target=','dim'),(state.domain,'bold white'),('  workspace=','dim'),(state.workspace,'blue'),('  elapsed=','dim'),(fmt_time(state.elapsed_seconds),'white'),('  status=','dim'),(state.overall_status,'green' if state.overall_status=='completed' else 'bright_cyan'),((f"  completed_via={state.completed_via}" if state.completed_via else ''),'green')), style='cyan')
    pipe=Table.grid(expand=True); pipe.add_column(ratio=1)
    for name, st in state.stages.items():
        style=STATUS_STYLES.get(st.status,'white'); glyph=STATUS_GLYPHS.get(st.status,'?'); msg=f" — {st.message}" if st.message else ''
        pipe.add_row(Text.assemble((glyph+' ',style),(name,style),(' '+st.status,'dim'),(msg,'dim')))
    pipeline=Panel(pipe, title='Pipeline', border_style='blue')
    if state.scheduler_started:
        operation=Panel('\n'.join(_slice_lines(state.last_completed_slice)), title='Last completed slice', border_style='bright_cyan')
    else:
        st=state.stages.get(state.current_stage); operation=Panel((st.message if st else 'waiting') or 'waiting', title='Current operation', border_style='bright_cyan')
    previous=Panel('\n'.join(_slice_lines(state.previous_completed_slice)), title='Previous completed slice', border_style='cyan')
    arm_panel=_build_arm_panel(state)
    recovered=_build_recovered_panel(state)
    footer=Panel(f"events={state.event_count}  warnings={state.warnings_count}  errors={state.errors_count}  recovered={state.recovered_candidate_count}  parsed_slices={len(state.slice_history)}", border_style='dim')
    layout=Layout(); layout.split_column(Layout(header,size=3), Layout(name='body'), Layout(footer,size=3))
    layout['body'].split_row(Layout(name='left',ratio=25), Layout(name='center',ratio=45), Layout(recovered,name='right',ratio=30))
    layout['left'].split_column(Layout(pipeline,ratio=3), Layout(_build_activity_panel(state),ratio=2))
    layout['center'].split_column(Layout(operation,ratio=1), Layout(previous,ratio=1), Layout(arm_panel,ratio=2))
    return layout
