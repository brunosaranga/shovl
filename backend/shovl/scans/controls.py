"""
Pause, resume and stop for a scan that is running.

The buttons on the scan page call POST /api/scans/<id>/pause/, /resume/ and /stop/
(ScanControlView). Those requests only change Scan.status. The stream that runs the scan
(scans/views.py) reads the status between two checks, so a check already in flight always
finishes first: a request to the target cannot be frozen halfway.

    running  --pause-->   paused  --resume-->  running
    running or paused  --stop-->  stopped

A stopped scan does not count against the allowance: scans/limits.py only counts complete
scans and ones still in progress.
"""
from django.utils import timezone

from .models import ACTIVE_STATUSES, Scan

# How often a paused stream looks for resume or stop: the longest a click waits to take effect.
PAUSE_POLL_SECONDS = 1

# The longest a scan may stay paused, added up over all its pauses. A paused scan holds one of
# the server's threads, so a forgotten tab must not keep it for long. With the 90-second scan
# budget this keeps every scan well inside the 10 minutes after which scans/limits.py calls it
# abandoned.
MAX_PAUSE_SECONDS = 5 * 60

STOPPED_MESSAGE = "You stopped this scan."
PAUSED_TOO_LONG_MESSAGE = (
    f"This scan was paused for more than {MAX_PAUSE_SECONDS // 60} minutes, so it was stopped."
)

# action: (the statuses it applies to, the status it leads to)
TRANSITIONS = {
    "pause": (("pending", "running"), "paused"),
    "resume": (("paused",), "running"),
    "stop": (ACTIVE_STATUSES, "stopped"),
}


def stopped_fields(reason, message):
    """What a stopped scan stores. The reason and message show on the dashboard and the report."""
    return {
        "status": "stopped",
        "results": {"error": {"reason": reason, "message": message}},
        "completed_at": timezone.now(),
    }


def current_status(scan_id):
    return Scan.objects.filter(pk=scan_id).values_list("status", flat=True).first()


def change(scan_id, action):
    """
    Apply pause, resume or stop if the scan's status allows it, as one conditional update, so
    two clicks (or a click and the stream finishing) can never both win. Returns the status the
    scan has afterwards: the one the action leads to, or the one that made it impossible.

    Asking for the state the scan is already in is fine: pausing a paused scan returns "paused".
    """
    sources, target = TRANSITIONS[action]
    if target == "stopped":
        fields = stopped_fields("stopped", STOPPED_MESSAGE)
    else:
        fields = {"status": target}
    Scan.objects.filter(pk=scan_id, status__in=sources).update(**fields)
    return current_status(scan_id)


def stop_paused_too_long(scan_id):
    """Stop a scan that has stayed paused past MAX_PAUSE_SECONDS. True if it was still paused."""
    return bool(
        Scan.objects.filter(pk=scan_id, status="paused").update(
            **stopped_fields("paused_too_long", PAUSED_TOO_LONG_MESSAGE)
        )
    )


def stop_details(scan_id):
    """(reason, message) for a scan that ended early, for the stream's "stopped" event."""
    results = Scan.objects.filter(pk=scan_id).values_list("results", flat=True).first()
    error = results.get("error") if isinstance(results, dict) else None
    if isinstance(error, dict):
        return error.get("reason", "stopped"), error.get("message", STOPPED_MESSAGE)
    return "stopped", STOPPED_MESSAGE
