from __future__ import annotations

class ConsoleEventPrinter:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def handle_event(self, event) -> None:
        print(format_event(event, self.verbose), flush=True)


def format_event(event, verbose: bool = False) -> str:
    line = f"[{event.stage}] {event.event}: {event.message}"
    if verbose and getattr(event, "data", None):
        selected = []
        for key in ("domain", "workspace", "dnssec_probe_enabled", "probe_status", "zone_type", "status", "hash_count", "completed_via"):
            if key in event.data:
                selected.append(f"{key}={event.data[key]}")
        if selected:
            line += " " + " ".join(selected)
    return line
