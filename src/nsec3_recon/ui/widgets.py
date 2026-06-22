from __future__ import annotations
from .theme import STATUS_GLYPHS, STATUS_STYLES

def fmt_time(sec):
    sec=int(sec or 0); return f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"

def _slice_lines(s):
    if not s: return ['no slice parsed yet']
    lines=[f"slice {s.get('slice_index','?')}/{s.get('total_slices','?')}  policy={s.get('schedule_name','?')}", f"arm={s.get('arm','?')} reason={s.get('reason','-')}"]
    lines.append(f"new={s.get('new','-')} total={s.get('total','-')} reward={s.get('reward','-')} runtime={s.get('runtime_seconds','-')}s")
    if s.get('score_before') is not None: lines.append(f"score {s.get('score_before')}→{s.get('score_after')}")
    if s.get('queue_before') is not None: lines.append(f"queue {s.get('queue_before')}→{s.get('queue_after')}")
    for name in ('skip','gate_queue','cooldown'):
        a=s.get(f'{name}_before') if name=='skip' else s.get(f'{name}_current')
        b=s.get(f'{name}_after') if name=='skip' else s.get(f'{name}_required')
        if a is not None: lines.append(f"{name} {a}→{b}")
    if s.get('progress'): lines.append(f"progress {s.get('progress')}")
    return lines

def build_dashboard(state):
    try:
        from rich.align import Align
        from rich.console import Group
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except Exception as e:
        raise RuntimeError('Rich is required for dashboard rendering') from e
    header=Panel(Text(f"NSEC3 RECON  target={state.domain}  workspace={state.workspace}  elapsed={fmt_time(state.elapsed_seconds)}  status={state.overall_status}" + (f"  completed_via={state.completed_via}" if state.completed_via else ''), style='bold bright_cyan'), style='cyan')
    pipe=Table.grid(expand=True); pipe.add_column(ratio=1)
    for name, st in state.stages.items():
        style=STATUS_STYLES.get(st.status,'white'); glyph=STATUS_GLYPHS.get(st.status,'?'); msg=f" — {st.message}" if st.message else ''
        pipe.add_row(Text.assemble((glyph+' ',style),(name,style),(' '+st.status,'dim'),(msg,'dim')))
    pipeline=Panel(pipe, title='Pipeline', border_style='blue')
    current_title='Current slice' if state.scheduler_started else 'Current operation'
    if state.scheduler_started: current=Panel('\n'.join(_slice_lines(state.current_slice)), title=current_title, border_style='bright_cyan')
    else:
        st=state.stages.get(state.current_stage); current=Panel((st.message if st else 'waiting') or 'waiting', title=current_title, border_style='bright_cyan')
    previous=Panel('\n'.join(_slice_lines(state.previous_slice)), title='Previous slice', border_style='cyan')
    act='\n'.join([f"[{a['level']}] {a['message']}" for a in list(state.recent_activity)[-10:]]) or 'no recent activity'
    activity=Panel(act, title='Recent activity', border_style='magenta')
    arms=Table(expand=True); [arms.add_column(c, no_wrap=True) for c in ('arm','runs','total_new','avg_reward','last_reward','avg_runtime','last_score','last_seen')]
    sorted_arms=sorted(state.arm_stats.values(), key=lambda a:(not a.active, -a.total_new, -a.avg_reward, -a.run_count))[:10]
    for a in sorted_arms: arms.add_row(('▶ '+a.name) if a.active else a.name, str(a.run_count), str(a.total_new), f"{a.avg_reward:.2f}", f"{a.last_reward:.2f}", f"{a.avg_runtime:.1f}s", '' if a.last_score is None else f"{a.last_score:.2f}", str(a.last_seen_slice or ''))
    arm_panel=Panel(arms, title='Arm statistics', border_style='green')
    top='\n'.join([f"{a.name}: new={a.total_new} score={a.last_score if a.last_score is not None else '-'}" for a in sorted_arms[:5]]) or 'waiting for scheduler slices'
    top_panel=Panel(top, title='Top arms / score snapshot', border_style='green')
    if state.recovered_candidates:
        rec='\n'.join([i['candidate'] for i in list(state.recovered_candidates)[:12]])
    else: rec='potfile not detected yet' if not state.current_potfile_path else 'waiting for recovered candidates'
    rec_panel=Panel(rec, title='Recovered candidates', border_style='yellow')
    footer=Panel(f"events={state.event_count} warnings={state.warnings_count} errors={state.errors_count} recovered={state.recovered_candidate_count} parsed_slices={len(state.slice_history)}", border_style='dim')
    layout=Layout(); layout.split_column(Layout(header,size=3), Layout(name='body'), Layout(footer,size=3))
    layout['body'].split_row(Layout(pipeline,name='left',ratio=1), Layout(name='center',ratio=2), Layout(name='right',ratio=2))
    layout['center'].split_column(Layout(current,ratio=1),Layout(previous,ratio=1),Layout(activity,ratio=1))
    layout['right'].split_column(Layout(arm_panel,ratio=2),Layout(top_panel,ratio=1),Layout(rec_panel,ratio=1))
    return layout
