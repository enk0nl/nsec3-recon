from ..events import utc_now

def run(ctx):
    ctx.events.emit('preflight','started','Preflight started')
    ctx.workspace.write_json('target.json', {'domain':ctx.config.domain,'created_at':utc_now(),'workspace':str(ctx.workspace.root)})
    ctx.workspace.write_json('config/pipeline_config.json', ctx.config.to_jsonable())
    ctx.events.emit('preflight','completed','Preflight completed')
