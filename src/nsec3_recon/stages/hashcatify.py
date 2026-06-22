from ..adapters.subprocess_runner import SubprocessRunner
from ..pipeline import PipelineError

def run(ctx):
    ctx.events.emit('hashcatify','started','hashcatify started')
    zone=ctx.workspace.root/'nsec3map/zone.txt'; hf=ctx.workspace.root/'nsec3map/nsec3map_hashfile.hash'
    res=SubprocessRunner().run([ctx.config.hashcatify_bin,str(zone),str(hf)], stdout_log=ctx.workspace.root/'nsec3map/hashcatify.stdout.log', stderr_log=ctx.workspace.root/'nsec3map/hashcatify.stderr.log')
    count=sum(1 for _ in hf.open()) if hf.exists() else 0
    obj={'status':'success' if res.returncode==0 and count else 'failed','hash_file':'nsec3map/nsec3map_hashfile.hash','hash_count':count,'elapsed_seconds':res.elapsed_seconds}
    ctx.workspace.write_json('nsec3map/hashcatify.json', obj); ctx.state['hashcatify']=obj
    if obj['status']!='success': ctx.events.emit('hashcatify','failed','hashcatify produced no hashes','error',obj); raise PipelineError('hashcatify','hashcatify produced no hashes')
    ctx.events.emit('hashcatify','completed','hashcatify completed', data=obj); return obj
