from nsec3_recon.events import PipelineEvent
from nsec3_recon.ui.console import ConsoleEventPrinter


def test_console_event_printer_outputs_stage_lines(capsys):
    printer = ConsoleEventPrinter()
    printer.handle_event(PipelineEvent('now','stage','info','event','message',{}))
    assert '[stage] event: message' in capsys.readouterr().out


def test_console_suppresses_python_deps_ok_in_normal_mode(capsys):
    printer = ConsoleEventPrinter()
    printer.handle_event(PipelineEvent('now','nsec3map','info','python_deps_ok','nsec3map Python dependencies available',{}))
    assert capsys.readouterr().out == ''


def test_console_prints_python_deps_ok_in_verbose_mode(capsys):
    printer = ConsoleEventPrinter(verbose=True)
    printer.handle_event(PipelineEvent('now','nsec3map','info','python_deps_ok','nsec3map Python dependencies available',{}))
    assert 'python_deps_ok' in capsys.readouterr().out


def test_console_always_prints_warnings_and_errors(capsys):
    printer = ConsoleEventPrinter()
    printer.handle_event(PipelineEvent('now','stage','warning','python_deps_ok','warn',{}))
    printer.handle_event(PipelineEvent('now','stage','error','dependency_check_ok','err',{}))
    out=capsys.readouterr().out
    assert 'warn' in out and 'err' in out
