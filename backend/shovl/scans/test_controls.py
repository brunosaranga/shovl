"""
Tests for pause, resume and stop: the endpoints (scans/controls.py, ScanControlView) and how
the stream reacts between two checks (hold_if_paused in scans/views.py).

The stream tests never touch the network: reachability and the checks are replaced, the
checks run in the test's own thread, and waiting while paused uses a fake clock.

Run with:  python manage.py test scans
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from scanner.engine import CHECK_INFO, CHECKS
from scanner.http import TimeBudget
from scans import controls, limits, views
from scans.models import Scan

User = get_user_model()

STREAM = "/api/scans/stream/"
PRACTICE = "https://postman-echo.com/get"
PASSWORD = "correct horse battery staple"
NAMES = [path.split(".")[-1] for path in CHECKS]


def control_url(scan_id, action):
    return f"/api/scans/{scan_id}/{action}/"


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def at_once(func, *args, **kwargs):
    """Stands in for views.while_working: runs the check in this thread, with no keep-alives."""
    return func(*args, **kwargs)
    yield  # never reached; makes this a generator, like the real one


class FakeClock:
    """time.monotonic for the stream. Every wait while paused moves it on by one second."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


def read(response):
    """The stream as a list: one dict per event, and "keep-alive" for each keep-alive line."""
    items = []
    for chunk in response.streaming_content:
        text = chunk.decode() if isinstance(chunk, bytes) else chunk
        if text.startswith(":"):
            items.append("keep-alive")
        elif text.startswith("data:"):
            items.append(json.loads(text[5:]))
    return items


def statuses(items):
    return [item if item == "keep-alive" else item["status"] for item in items]


class TimeBudgetExtendTests(SimpleTestCase):
    def test_extend_gives_time_back(self):
        clock = SimpleNamespace(now=0.0)
        budget = TimeBudget(seconds=10, clock=lambda: clock.now)
        clock.now = 8.0
        self.assertAlmostEqual(budget.remaining(), 2.0)
        budget.extend(5)
        self.assertAlmostEqual(budget.remaining(), 7.0)

    def test_extend_never_takes_time_away(self):
        budget = TimeBudget(seconds=10, clock=lambda: 0.0)
        budget.extend(-5)
        self.assertAlmostEqual(budget.remaining(), 10.0)


class ControlEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner@example.com", PASSWORD, tos_agreed=True)
        self.client = signed_in(self.user)

    def make_scan(self, status="running", user=None):
        return Scan.objects.create(user=user or self.user, target_url=PRACTICE, status=status)

    def post(self, scan_id, action, client=None):
        return (client or self.client).post(control_url(scan_id, action))

    def test_pause_then_resume(self):
        scan = self.make_scan()

        response = self.post(scan.pk, "pause")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"id": scan.pk, "status": "paused"})

        response = self.post(scan.pk, "resume")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "running")

    def test_asking_for_the_state_it_is_already_in_is_fine(self):
        scan = self.make_scan("paused")
        self.assertEqual(self.post(scan.pk, "pause").data["status"], "paused")

        scan = self.make_scan("running")
        self.assertEqual(self.post(scan.pk, "resume").data["status"], "running")

    def test_stop_is_recorded_at_once_with_a_reason(self):
        for start in ("running", "paused", "pending"):
            scan = self.make_scan(start)
            response = self.post(scan.pk, "stop")
            self.assertEqual(response.status_code, 200, start)
            self.assertEqual(response.data["status"], "stopped")

            scan.refresh_from_db()
            self.assertEqual(scan.status, "stopped")
            self.assertIsNotNone(scan.completed_at)
            self.assertEqual(scan.results["error"]["reason"], "stopped")
            self.assertEqual(scan.results["error"]["message"], controls.STOPPED_MESSAGE)

        # A second stop changes nothing and still answers 200.
        again = self.post(scan.pk, "stop")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data["status"], "stopped")

    def test_a_scan_that_already_ended_answers_409(self):
        cases = [
            ("complete", "pause"),
            ("complete", "stop"),
            ("failed", "resume"),
            ("interrupted", "stop"),
            ("stopped", "pause"),
            ("stopped", "resume"),
        ]
        for status, action in cases:
            scan = self.make_scan(status)
            response = self.post(scan.pk, action)
            self.assertEqual(response.status_code, 409, (status, action))
            self.assertEqual(response.data["code"], "scan_finished")
            self.assertEqual(response.data["status"], status)
            scan.refresh_from_db()
            self.assertEqual(scan.status, status, "a finished scan is never changed")

    def test_only_the_owner_can_control_a_scan(self):
        someone_else = User.objects.create_user("other@example.com", PASSWORD, tos_agreed=True)
        scan = self.make_scan(user=someone_else)

        for action in ("pause", "resume", "stop"):
            self.assertEqual(self.post(scan.pk, action).status_code, 404, action)
        scan.refresh_from_db()
        self.assertEqual(scan.status, "running")

        self.assertEqual(self.post(999999, "stop").status_code, 404)

    def test_signing_in_is_required(self):
        scan = self.make_scan()
        self.assertEqual(APIClient().post(control_url(scan.pk, "stop")).status_code, 401)

    def test_a_guest_can_stop_their_own_scan(self):
        guest = User.objects.create_guest(tos_agreed=True)
        scan = self.make_scan(user=guest)
        self.assertEqual(self.post(scan.pk, "stop", client=signed_in(guest)).status_code, 200)

    def test_only_post_is_accepted(self):
        scan = self.make_scan()
        self.assertEqual(self.client.get(control_url(scan.pk, "stop")).status_code, 405)


class AllowanceTests(TestCase):
    def setUp(self):
        self.guest = User.objects.create_guest(tos_agreed=True)

    def test_a_paused_scan_counts_and_a_stopped_one_does_not(self):
        scan = Scan.objects.create(user=self.guest, target_url=PRACTICE, status="paused")
        self.assertEqual(limits.scans_remaining(self.guest)["used"], 1)

        controls.change(scan.pk, "stop")
        self.assertEqual(limits.scans_remaining(self.guest)["used"], 0)


class StreamControlTests(TestCase):
    """The stream with pause, resume and stop arriving while it runs."""

    def setUp(self):
        self.user = User.objects.create_user("bruno@example.com", PASSWORD, tos_agreed=True)
        self.client = signed_in(self.user)

        self.checks_run = []          # check names, in the order they ran
        self.during_check = {}        # check index -> action to apply while it runs
        self.while_paused = []        # actions to apply on each wait while paused, in order
        self.checks_run_at_wait = []  # how many checks had run at each wait
        self.clock = FakeClock()

        for target, value in [
            ("preflight", lambda *args, **kwargs: None),
            ("while_working", at_once),
            ("run_check", self.fake_check),
            ("_sleep", self.fake_sleep),
            ("time", SimpleNamespace(monotonic=self.clock.monotonic)),
        ]:
            patcher = patch.object(views, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    # ---- stand-ins ------------------------------------------------------------------

    def scan_id(self):
        return Scan.objects.get().pk

    def fake_check(self, module_path, target_url, token=None, verbose=False, budget=None, allow_writes=False):
        index = len(self.checks_run)
        self.checks_run.append(module_path.split(".")[-1])
        if index in self.during_check:
            controls.change(self.scan_id(), self.during_check[index])
        name, check_id = CHECK_INFO[module_path]
        return {"check": name, "id": check_id, "severity": "PASS", "detail": ["fine"]}

    def fake_sleep(self, seconds):
        self.clock.now += 1
        self.checks_run_at_wait.append(len(self.checks_run))
        if self.while_paused:
            action = self.while_paused.pop(0)
            if action:
                controls.change(self.scan_id(), action)

    def run_stream(self):
        response = self.client.get(STREAM, {"target_url": PRACTICE})
        self.assertEqual(response.status_code, 200)
        return read(response)

    # ---- tests ----------------------------------------------------------------------

    def test_the_scan_id_comes_first(self):
        items = self.run_stream()
        self.assertEqual(items[0], {"status": "started", "scan_id": self.scan_id(), "total": len(CHECKS)})

    def test_without_any_click_the_scan_completes_as_before(self):
        items = self.run_stream()
        self.assertEqual(statuses(items)[-1], "complete")
        self.assertEqual(self.checks_run, NAMES)
        self.assertEqual(Scan.objects.get().status, "complete")
        self.assertEqual(self.checks_run_at_wait, [], "a scan nobody paused never waits")

    def test_pause_holds_the_scan_between_two_checks_until_resume(self):
        self.during_check = {1: "pause"}                # clicked while the 2nd check runs
        self.while_paused = [None, "resume"]            # resumed on the 2nd look

        with patch.object(TimeBudget, "extend", autospec=True) as extend:
            items = self.run_stream()

        names = statuses(items)
        paused_at = names.index("paused")
        # The check in flight finished first, then the scan held before the 3rd check.
        self.assertEqual(items[paused_at - 1]["status"], "result")
        self.assertEqual(items[paused_at - 1]["check"], NAMES[1])
        self.assertEqual(names[paused_at + 1], "resumed")
        self.assertEqual(items[paused_at + 2], {"status": "running", "check": NAMES[2], "progress": 2, "total": len(CHECKS)})
        # Nothing ran while paused, and every check ran in the end.
        self.assertEqual(self.checks_run_at_wait, [2, 2])
        self.assertEqual(self.checks_run, NAMES)
        self.assertEqual(names[-1], "complete")
        self.assertEqual(Scan.objects.get().status, "complete")
        # The two paused seconds were given back to the time budget.
        extend.assert_called_once()
        self.assertAlmostEqual(extend.call_args.args[1], 2.0)

    def test_keep_alive_lines_while_paused(self):
        self.during_check = {0: "pause"}
        self.while_paused = [None, None, None, "resume"]

        with patch.object(views, "KEEP_ALIVE_SECONDS", 1):
            names = statuses(self.run_stream())

        between = names[names.index("paused") + 1:names.index("resumed")]
        self.assertGreaterEqual(between.count("keep-alive"), 3)

    def test_stop_ends_the_scan_at_the_next_check(self):
        self.during_check = {1: "stop"}
        items = self.run_stream()

        self.assertEqual(items[-1], {
            "status": "stopped", "scan_id": self.scan_id(),
            "reason": "stopped", "message": controls.STOPPED_MESSAGE,
        })
        self.assertEqual(self.checks_run, NAMES[:2], "no check starts after a stop")
        scan = Scan.objects.get()
        self.assertEqual(scan.status, "stopped")
        self.assertEqual(limits.scans_remaining(self.user)["used"], 0, "a stopped scan does not count")

    def test_stop_while_paused(self):
        self.during_check = {0: "pause"}
        self.while_paused = [None, "stop"]
        names = statuses(self.run_stream())

        self.assertEqual(names[-2:], ["paused", "stopped"])
        self.assertEqual(self.checks_run, NAMES[:1])
        self.assertEqual(Scan.objects.get().status, "stopped")

    def test_a_stop_during_the_last_check_is_never_overwritten(self):
        self.during_check = {len(CHECKS) - 1: "stop"}
        names = statuses(self.run_stream())

        self.assertEqual(names[-1], "stopped")
        self.assertEqual(Scan.objects.get().status, "stopped")

    def test_a_stop_while_the_report_is_built_is_never_overwritten(self):
        real_format = views.format_report

        def format_then_stop(raw):
            report = real_format(raw)
            controls.change(self.scan_id(), "stop")
            return report

        with patch.object(views, "format_report", format_then_stop):
            names = statuses(self.run_stream())

        self.assertEqual(names[-1], "stopped")
        scan = Scan.objects.get()
        self.assertEqual(scan.status, "stopped")
        self.assertEqual(scan.results["error"]["reason"], "stopped")

    def test_a_scan_paused_too_long_is_stopped(self):
        self.during_check = {0: "pause"}
        with patch.object(controls, "MAX_PAUSE_SECONDS", 3):
            items = self.run_stream()

        self.assertEqual(self.checks_run_at_wait, [1, 1, 1], "stopped on the third second")
        self.assertEqual(items[-1]["status"], "stopped")
        self.assertEqual(items[-1]["reason"], "paused_too_long")
        self.assertEqual(Scan.objects.get().results["error"]["message"], controls.PAUSED_TOO_LONG_MESSAGE)

    def test_the_pause_limit_adds_up_over_several_pauses(self):
        # Two seconds paused before check 2, then the third second runs out during the next pause.
        self.during_check = {0: "pause", 2: "pause"}
        self.while_paused = [None, "resume"]
        with patch.object(controls, "MAX_PAUSE_SECONDS", 3):
            items = self.run_stream()

        self.assertEqual(statuses(items).count("paused"), 2)
        self.assertEqual(items[-1]["reason"], "paused_too_long")
        self.assertEqual(self.checks_run, NAMES[:3])
        self.assertEqual(len(self.checks_run_at_wait), 3)

    def test_leaving_while_paused_marks_the_scan_interrupted(self):
        self.during_check = {0: "pause"}
        response = self.client.get(STREAM, {"target_url": PRACTICE})

        for chunk in response.streaming_content:
            if b'"paused"' in (chunk if isinstance(chunk, bytes) else chunk.encode()):
                break

        # What the server does when the browser goes away. Closing a response also ends the request,
        # which would close this test's database connection (Postgres; SQLite ignores it), so that
        # one step is skipped here.
        with patch.object(connections["default"], "close_if_unusable_or_obsolete"):
            response.close()

        self.assertEqual(Scan.objects.get().status, "interrupted")

    def test_a_failed_check_run_after_a_stop_keeps_the_stop(self):
        # Every check came back as ERROR (the scan fails), but the person had stopped it first.
        scan = Scan.objects.create(user=self.user, target_url=PRACTICE, status="stopped")
        self.assertFalse(views.mark_failed(scan, "timeout", "Too slow."))
        scan.refresh_from_db()
        self.assertEqual(scan.status, "stopped")
