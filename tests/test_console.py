from nsec3_recon.events import PipelineEvent
from nsec3_recon.ui.console import ConsoleEventPrinter


def test_console_event_printer_outputs_stage_lines(capsys):
    printer = ConsoleEventPrinter()
    printer.handle_event(PipelineEvent('now','stage','info','event','message',{}))
    assert '[stage] event: message' in capsys.readouterr().out
