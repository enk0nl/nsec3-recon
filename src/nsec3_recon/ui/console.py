from __future__ import annotations

SUPPRESSED_SUCCESS_EVENTS = {
    "python_deps_ok",
    "dependency_check_ok",
    "tool_version_ok",
    "model_assets_ok",
    "path_check_ok",
}

class ConsoleEventPrinter:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def handle_event(self, event) -> None:
        if not should_print_event(event, self.verbose):
            return
        print(format_event(event, self.verbose), flush=True)


def should_print_event(event, verbose: bool = False) -> bool:
    if event.level in {"error", "warning"}:
        return True
    if event.level == "debug":
        return verbose
    if not verbose and event.event in SUPPRESSED_SUCCESS_EVENTS:
        return False
    return True


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
