from ..adapters.scheduler import render_scheduler_config
from ..adapters.subprocess_runner import SubprocessRunner
from ..pipeline import PipelineError

def run(ctx):
    ctx.events.emit('scheduler','started','scheduler started')
    cfg=ctx.workspace.root/'config/scheduler_config.json'
    render_scheduler_config(ctx.config.domain, ctx.config.assets_dir, cfg, ctx.config.scheduler_config)
    cmd=ctx.config.scheduler_command(ctx.workspace.root, ctx.workspace.root/'nsec3map/nsec3map_hashfile.hash', cfg)
    ctx.state['scheduler_command']=cmd
    res=SubprocessRunner().run(cmd, stdout_log=ctx.workspace.root/'scheduler/stdout.log', stderr_log=ctx.workspace.root/'scheduler/stderr.log', stream=True, on_stdout=lambda l: ctx.events.emit('scheduler','stdout',l), on_stderr=lambda l: ctx.events.emit('scheduler','stderr',l,'warning'))
    ctx.state['scheduler']={'exit_code':res.returncode,'elapsed_seconds':res.elapsed_seconds}
    if res.returncode!=0: raise PipelineError('scheduler','scheduler failed')
    ctx.events.emit('scheduler','completed','scheduler completed'); return ctx.state['scheduler']
