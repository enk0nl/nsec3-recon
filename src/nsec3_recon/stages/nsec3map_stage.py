from ..adapters.subprocess_runner import SubprocessRunner
from ..adapters.nsec3map import classify_zone_file
from ..pipeline import PipelineError

def run(ctx):
    ctx.events.emit('nsec3map','started','nsec3map started')
    zone=ctx.workspace.root/'nsec3map/zone.txt'; out=ctx.workspace.root/'nsec3map/n3map.stdout.log'; err=ctx.workspace.root/'nsec3map/n3map.stderr.log'
    cmd=[ctx.config.nsec3map_bin,'-v','-o',str(zone),ctx.config.domain]
    res=SubprocessRunner().run(cmd, stdout_log=out, stderr_log=err)
    status='success' if res.returncode==0 else 'failed'; zt=classify_zone_file(zone)
    obj={'domain':ctx.config.domain,'status':status,'zone_type':zt,'zone_file':'nsec3map/zone.txt','stdout_log':'nsec3map/n3map.stdout.log','stderr_log':'nsec3map/n3map.stderr.log','exit_code':res.returncode,'elapsed_seconds':res.elapsed_seconds}
    ctx.workspace.write_json('nsec3map/result.json', obj); ctx.state['nsec3map']=obj
    if res.returncode!=0: ctx.events.emit('nsec3map','failed','nsec3map failed','error',obj); raise PipelineError('nsec3map','nsec3map failed')
    ctx.events.emit('nsec3map','completed','nsec3map completed', data=obj); return obj
