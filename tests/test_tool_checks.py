import json, os, subprocess
from pathlib import Path
import pytest
from nsec3_recon.adapters import tools
from nsec3_recon.config import PipelineConfig
from nsec3_recon.pipeline import Pipeline, PipelineError

def make_tool(tmp_path, name, output):
    p=tmp_path/name
    p.write_text(f'#!/usr/bin/env sh\necho "{output}"\n')
    p.chmod(0o755)
    return p

def test_check_tools_flags_old_hashcat(tmp_path):
    make_tool(tmp_path, 'hashcat', 'v6.2.6')
    env=os.environ|{'PATH':f'{tmp_path}:{os.environ["PATH"]}', 'PYTHONPATH':'src'}
    cp=subprocess.run(['bash','scripts/check-tools.sh','--no-osint'], text=True, capture_output=True, env=env)
    assert cp.returncode != 0
    assert '[bad-version] hashcat version=6.2.6 required>=7.1.2' in cp.stdout

def test_check_tools_accepts_hashcat_712(tmp_path):
    make_tool(tmp_path, 'hashcat', 'v7.1.2')
    env=os.environ|{'PATH':f'{tmp_path}:{os.environ["PATH"]}', 'PYTHONPATH':'src'}
    cp=subprocess.run(['bash','scripts/check-tools.sh','--no-osint'], text=True, capture_output=True, env=env)
    assert '[ok] hashcat version=7.1.2 required>=7.1.2' in cp.stdout

def test_runtime_preflight_fails_if_osint_amass_enabled_and_missing(monkeypatch, tmp_path):
    from nsec3_recon.stages import scheduler_stage
    monkeypatch.setattr(tools, 'check_hashcat', lambda path='hashcat': tools.ToolCheck('hashcat','hashcat','7.1.2',(7,1,2),True))
    monkeypatch.setattr(tools, 'check_amass', lambda path='/x': tools.ToolCheck('amass',None,'5.1.1',None,False))
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r')).setup()
    with pytest.raises(PipelineError): scheduler_stage.run(ctx)

def test_runtime_preflight_ignores_missing_amass_if_arm_disabled(monkeypatch, tmp_path):
    from nsec3_recon.stages import scheduler_stage
    cfg=tmp_path/'sched.json'
    data=json.loads(Path('src/nsec3_recon/templates/scheduler_config.json').read_text().replace('{{ domain }}','example.nl'))
    for arm in data['arms']:
        if arm['name']=='osint/amass': arm['enabled']=False
        if arm['name']=='osint/subfinder': arm['enabled']=False
    cfg.write_text(json.dumps(data))
    monkeypatch.setattr(tools, 'check_hashcat', lambda path='hashcat': tools.ToolCheck('hashcat','hashcat','7.1.2',(7,1,2),True))
    monkeypatch.setattr('nsec3_recon.stages.scheduler_stage.SubprocessRunner.run', lambda *a, **k: type('R',(),{'returncode':0,'elapsed_seconds':0})())
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r', scheduler_config=cfg)).setup()
    scheduler_stage.run(ctx)

def test_runtime_preflight_fails_if_subfinder_enabled_and_old(monkeypatch, tmp_path):
    from nsec3_recon.stages import scheduler_stage
    monkeypatch.setattr(tools, 'check_hashcat', lambda path='hashcat': tools.ToolCheck('hashcat','hashcat','7.1.2',(7,1,2),True))
    monkeypatch.setattr(tools, 'check_amass', lambda path='/x': tools.ToolCheck('amass','amass','5.1.1',(5,1,1),True))
    monkeypatch.setattr(tools, 'check_subfinder', lambda path='/x': tools.ToolCheck('subfinder','subfinder','2.14.0',(2,13,0),False))
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r')).setup()
    with pytest.raises(PipelineError): scheduler_stage.run(ctx)
