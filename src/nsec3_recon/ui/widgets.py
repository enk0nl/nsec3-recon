from __future__ import annotations
from .theme import STATUS_GLYPHS, STATUS_STYLES
import shutil
import textwrap

ARM_ROW_LIMIT = 16
RECOVERED_ROW_LIMIT = 24
ACTIVITY_ROW_LIMIT = 10

def fmt_time(sec):
    sec=int(sec or 0); return f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"

def shorten_middle(value: str, max_len: int = 28) -> str:
    value = value or ''
    if len(value) <= max_len: return value
    keep = max_len - 1
    left = max(8, min(keep, (keep * 2) // 3))
    right = keep - left
    return value[:left] + '…' + value[-right:]

def format_slice_index(slice_index, total_slices, fallback_total_slices=None):
    total = total_slices if total_slices is not None else fallback_total_slices
    return f"{slice_index if slice_index is not None else '?'}/{total if total is not None else '?'}"

def _slice_lines(s, fallback_total_slices=None):
    if not s: return ['waiting for previous completed slice…']
    phase=s.get('phase') or s.get('schedule_name') or 'unknown'
    label='job' if s.get('source') == 'jobs_jsonl' or s.get('job_id') is not None else 'slice'
    lines=[f"{label} {format_slice_index(s.get('slice_index') or s.get('job_id'), s.get('total_slices'), fallback_total_slices)}  phase={phase}", f"arm={s.get('arm','?')}  reason={s.get('reason','-')}"]
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
    return '–' if value is None else f"{float(value):.{ndigits}f}"

def _fmt_runtime(value):
    return '–' if value is None else f"{float(value):.1f}s"

def _fmt_progress(value):
    if value is None: return '–'
    return f"{value:.2f}%" if value < 1 else f"{value:.1f}%"

def compute_arm_stats_visible_rows(console_height=None, layout_height=None):
    height = layout_height if layout_height is not None else console_height
    if height is None:
        height = shutil.get_terminal_size(fallback=(120, 40)).lines
    if height >= 50:
        return 16
    if height >= 44:
        return 14
    if height >= 38:
        return 12
    if height >= 32:
        return 10
    return 8

def compute_arm_table_max_rows(terminal_height=None):
    return compute_arm_stats_visible_rows(console_height=terminal_height)

def _panel_body_height(options, fallback):
    max_height = getattr(options, 'max_height', None) or 0
    if max_height > 0:
        return max(0, max_height - 2)
    return fallback

def _content_width(options, fallback=80):
    max_width = getattr(options, 'max_width', None) or 0
    return max(1, (max_width or fallback) - 4)

def _truncate_end(value: str, max_len: int) -> str:
    value = str(value or '')
    if len(value) <= max_len:
        return value
    return value[:max(1, max_len - 1)] + '…'

def _one_line_text(value, style='', width=80, preserve_prefix=False):
    from rich.text import Text
    max_len=max(1, width)
    text = _truncate_end(value, max_len) if preserve_prefix else shorten_middle(str(value or ''), max_len)
    return Text(text, style=style, no_wrap=True, overflow='ellipsis')

def _panel_height(options, body_height):
    max_height = getattr(options, 'max_height', None) or 0
    return max_height if max_height > 0 else body_height + 2

def _wrap_lines(value, width):
    text=str(value or '')
    return textwrap.wrap(text, width=max(1, width), replace_whitespace=False, drop_whitespace=False) or ['']

def _pad_text_lines(lines, body_height):
    from rich.text import Text
    padded=list(lines)
    while len(padded) < body_height:
        padded.append(Text(''))
    return padded

def _sorted_arms(state):
    def arm_sort_key(a):
        score = a.last_score if a.last_score is not None else float('-inf')
        return (bool(getattr(a, 'exhausted', False)), -score, -a.total_new, -a.last_reward, -a.run_count, a.name)
    return sorted(state.arm_stats.values(), key=arm_sort_key)

class ArmStatisticsPanel:
    def __init__(self, state, max_rows=None):
        self.state=state; self.max_rows=max_rows
    def __rich_console__(self, console, options):
        from rich.panel import Panel
        body_height = self.max_rows + 1 if self.max_rows is not None else _panel_body_height(options, compute_arm_stats_visible_rows())
        available_arm_rows = max(0, body_height - 1)  # table header uses one body row
        sorted_arms=_sorted_arms(self.state)
        visible_arms = sorted_arms[:available_arm_rows]
        hidden=max(0, len(sorted_arms)-len(visible_arms))
        subtitle = f"+{hidden} more arms" if hidden > 0 else None
        yield Panel(_arm_table(self.state, visible_arms, _content_width(options), pad_rows=max(0, available_arm_rows-len(visible_arms)) if hidden == 0 else 0), title='Arm statistics', subtitle=subtitle, border_style='green', height=_panel_height(options, body_height))

def _arm_table(state, visible_arms, width, pad_rows=0):
    from rich.table import Table
    arms = Table(expand=True, show_edge=False, box=None, pad_edge=False)
    arms.add_column('Arm', overflow='ellipsis', ratio=3, no_wrap=True)
    for col in ('Runs','Total','Last','R','Score','Avg t','Seen'):
        arms.add_column(col, justify='right', no_wrap=True, overflow='ellipsis')
    for a in visible_arms:
        arm_name = shorten_middle(a.name, max(12, min(30, width - 50)))
        if a.name == getattr(state, 'last_scheduled_arm', None): arm_name = '▶ ' + arm_name
        row_style = 'dim' if getattr(a, 'exhausted', False) and not a.active else None
        arms.add_row(arm_name, str(a.run_count), str(a.total_new), str(a.last_new), _fmt_float(a.last_reward), _fmt_float(a.last_score), _fmt_runtime(a.avg_runtime), str(a.last_seen_slice or '-'), style=row_style)
    if not visible_arms and not state.arm_stats:
        arms.add_row('waiting for scheduler slices', '', '', '', '', '', '', '')
        pad_rows=max(0, pad_rows-1)
    for _ in range(pad_rows):
        arms.add_row('', '', '', '', '', '', '', '')
    return arms

def _build_arm_panel(state, max_rows=None):
    return ArmStatisticsPanel(state, max_rows=max_rows)

class DiscoveredNamesPanel:
    def __init__(self, state, max_rows=None):
        self.state=state; self.max_rows=max_rows
    def __rich_console__(self, console, options):
        from rich.panel import Panel
        from rich.text import Text
        body_height = self.max_rows if self.max_rows is not None else _panel_body_height(options, RECOVERED_ROW_LIMIT)
        rows=list(self.state.discovered_names_recent)[-body_height:] if body_height > 0 else []
        width=_content_width(options)
        lines=[]
        if rows:
            for item in rows:
                timestamp=getattr(item, 'first_seen_at', '--:--:--'); name=getattr(item, 'name', '')
                shown_name=_truncate_end(name, max(1, width - len(timestamp) - 2))
                row=Text.assemble((timestamp, 'cyan'), ('  ', 'cyan'), (shown_name, 'bold white'))
                row.no_wrap=True; row.overflow='ellipsis'
                lines.append(row)
        else:
            msg='potfile not detected yet' if not self.state.current_potfile_path and not self.state.discovered_names_by_source else 'waiting for discovered names…'
            lines.append(Text(msg, style='dim', no_wrap=True, overflow='ellipsis'))
        lines=_pad_text_lines(lines, body_height)
        source = _discovered_source_label(self.state)
        yield Panel(Text('\n').join(lines), title='Discovered names', subtitle=f"total={self.state.discovered_names_count}  source: {source}", border_style='bright_yellow', height=_panel_height(options, body_height))

def _build_discovered_panel(state, max_rows=None):
    return DiscoveredNamesPanel(state, max_rows=max_rows)

def _discovered_source_label(state):
    if len(state.discovered_names_by_source) > 1:
        return ','.join(sorted(state.discovered_names_by_source))
    if len(state.discovered_names_by_source) == 1:
        only=next(iter(state.discovered_names_by_source))
        return only
    if state.current_potfile_path:
        return 'nsec3'
    return 'none'

class RecentActivityPanel:
    def __init__(self, state, max_rows=None):
        self.state=state; self.max_rows=max_rows
    def __rich_console__(self, console, options):
        from rich.panel import Panel
        from rich.text import Text
        body_height = self.max_rows if self.max_rows is not None else _panel_body_height(options, ACTIVITY_ROW_LIMIT)
        width=_content_width(options)
        style_by_level={'warning':'yellow','error':'red','info':'white','debug':'dim'}
        selected=[]; used_rows=0
        for activity in reversed(list(self.state.recent_activity)):
            style=style_by_level.get(activity.get('level'), 'white')
            wrapped=_wrap_lines(activity.get('message'), width)
            rows=len(wrapped)
            if selected and used_rows + rows > body_height:
                break
            if not selected and rows > body_height:
                wrapped=wrapped[:body_height]
                rows=len(wrapped)
            selected.append((wrapped, style)); used_rows += rows
            if used_rows >= body_height:
                break
        selected.reverse()
        lines=[]
        for wrapped, style in selected:
            lines.extend(Text(line, style=style) for line in wrapped)
        if not lines:
            lines.append(Text('no recent activity', style='dim'))
        lines=_pad_text_lines(lines, body_height)
        yield Panel(Text('\n').join(lines), title='Recent activity', border_style='blue', height=_panel_height(options, body_height))

def _build_activity_panel(state, max_rows=None):
    return RecentActivityPanel(state, max_rows=max_rows)


def _status_line(state):
    return (
        f"events={state.event_count}  "
        f"warnings={state.warnings_count}  "
        f"errors={state.errors_count}  "
        f"hashes={state.nsec3_hash_cracked}/{state.nsec3_hash_total or '?'} "
        f"({_fmt_progress(state.nsec3_hash_progress_percent)})  "
        f"parsed_slices={len(state.slice_history)}"
    )

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
        operation=Panel('\n'.join(_slice_lines(state.last_completed_slice, state.scheduler_total_slices)), title='Last completed slice', border_style='bright_cyan')
    else:
        st=state.stages.get(state.current_stage); operation=Panel((st.message if st else 'waiting') or 'waiting', title='Current operation', border_style='bright_cyan')
    previous=Panel('\n'.join(_slice_lines(state.previous_completed_slice, state.scheduler_total_slices)), title='Previous completed slice', border_style='cyan')
    arm_panel=_build_arm_panel(state)
    discovered=_build_discovered_panel(state)
    footer=Panel(_status_line(state), border_style='dim')
    layout=Layout(); layout.split_column(Layout(header,size=3), Layout(name='body'), Layout(footer,size=3))
    layout['body'].split_row(Layout(name='left',ratio=25), Layout(name='center',ratio=45), Layout(discovered,name='right',ratio=30))
    layout['left'].split_column(Layout(pipeline,ratio=3), Layout(_build_activity_panel(state),ratio=2))
    layout['center'].split_column(Layout(operation,ratio=1), Layout(previous,ratio=1), Layout(arm_panel,ratio=2))
    return layout
