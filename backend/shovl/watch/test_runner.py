"""
The runner (watch/runner.py), the run_watches command, rule A (three failed re-checks put the
domain back to pending and pause its watches), watches restarting when the domain is
verified again, and watches coming forward when their plan's cadence gets shorter.

Nothing here touches the network: the engine and the verification checks are replaced.

Run with:  DJANGO_DEBUG=1 python manage.py test watch
"""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from domains.models import Domain
from scanner.engine import CHECK_INFO, CHECKS, ScanFailed, build_raw
from scans import limits
from scans.models import TRIGGER_WATCH, Scan
from watch import runner, services
from watch.models import Watch

User = get_user_model()

PASSWORD = "correct horse battery staple"
HOST = "api.example.com"
API = f"https://{HOST}/v1"


def registered(email="real@example.com", **fields):
    return User.objects.create_user(email, PASSWORD, tos_agreed=True, **fields)


def domain_for(user, hostname=HOST, method="dns"):
    return Domain.objects.create(
        user=user, hostname=hostname, verified=True, verified_at=timezone.now(), verification_method=method,
    )


def make_watch(user, domain, url=API, due_in=timedelta(minutes=-1), **fields):
    return Watch.objects.create(
        user=user, domain=domain, target_url=url, next_run_at=timezone.now() + due_in, **fields
    )


def findings(severity="PASS", overrides=None):
    overrides = overrides or {}
    result = []
    for path in CHECKS:
        name, check_id = CHECK_INFO[path]
        result.append({"check": name, "id": check_id, "severity": overrides.get(check_id, severity), "detail": ["x"]})
    return result


def fake_scan(severity="PASS", overrides=None):
    def run(target_url, **kwargs):
        return build_raw(target_url, findings(severity, overrides), kwargs.get("verbose", False), kwargs.get("suggest_fix", False))
    return run


class RunnerTestCase(TestCase):
    """Replaces the engine with an all-PASS scan and the re-check with a pass, unless a test says otherwise."""

    def setUp(self):
        self.user = registered()
        self.domain = domain_for(self.user)
        self.scan_patch = patch.object(runner, "run_scan", side_effect=fake_scan())
        self.dns_patch = patch.object(runner, "verify_dns", return_value=True)
        self.file_patch = patch.object(runner, "verify_file", return_value=True)
        self.run_scan = self.scan_patch.start()
        self.verify_dns = self.dns_patch.start()
        self.verify_file = self.file_patch.start()
        self.addCleanup(patch.stopall)

    def run_one(self, watch):
        return runner.run_watch(watch, timezone.now(), {})


class DueWatchesTests(RunnerTestCase):
    def test_due_active_in_plan_watches_most_overdue_first(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        later = make_watch(self.user, self.domain, API, due_in=timedelta(minutes=-5))
        earlier = make_watch(self.user, self.domain, f"https://{HOST}/v2", due_in=timedelta(hours=-3))
        make_watch(self.user, self.domain, f"https://{HOST}/v3", due_in=timedelta(hours=1))
        self.assertEqual(runner.due_watches(timezone.now()), [earlier, later])

    def test_left_out(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        make_watch(self.user, self.domain, f"https://{HOST}/off", active=False)
        paused = make_watch(self.user, self.domain, f"https://{HOST}/paused")
        paused.pause(Watch.PAUSED_FAILURES)
        self.assertEqual(runner.due_watches(timezone.now()), [])

    def test_account_switch_off_or_account_inactive(self):
        make_watch(self.user, self.domain)
        self.user.watch_enabled = False
        self.user.save()
        self.assertEqual(runner.due_watches(timezone.now()), [])
        self.user.watch_enabled = True
        self.user.is_active = False
        self.user.save()
        self.assertEqual(runner.due_watches(timezone.now()), [])

    def test_only_the_watches_that_fit_the_plan(self):
        now = timezone.now()
        first = make_watch(self.user, self.domain, API, activated_at=now - timedelta(days=2))
        make_watch(self.user, self.domain, f"https://{HOST}/v2", activated_at=now - timedelta(days=1))
        self.assertEqual(runner.due_watches(now), [first])


class ClaimAndStaleTests(RunnerTestCase):
    def test_claim_books_a_retry_and_counts_a_failure_up_front(self):
        watch = make_watch(self.user, self.domain)
        now = timezone.now()
        self.assertTrue(runner.claim(watch, now))
        self.assertEqual(watch.next_run_at, now + runner.RETRY_DELAY)
        self.assertEqual(watch.consecutive_failures, 1)

    def test_a_watch_that_changed_is_not_claimed(self):
        watch = make_watch(self.user, self.domain)
        stale_copy = Watch.objects.get(pk=watch.pk)
        self.assertTrue(runner.claim(watch, timezone.now()))
        self.assertFalse(runner.claim(stale_copy, timezone.now()))

    def test_left_behind_scheduled_scans_are_interrupted(self):
        old = timezone.now() - runner.STALE_AFTER - timedelta(minutes=1)
        stale = Scan.objects.create(user=self.user, target_url=API, status="running", trigger=TRIGGER_WATCH)
        fresh = Scan.objects.create(user=self.user, target_url=API, status="running", trigger=TRIGGER_WATCH)
        manual = Scan.objects.create(user=self.user, target_url=API, status="running")
        Scan.objects.filter(pk__in=[stale.pk, manual.pk]).update(created_at=old)
        self.assertEqual(runner.sweep_stale_scans(timezone.now()), 1)
        statuses = dict(Scan.objects.values_list("pk", "status"))
        self.assertEqual(statuses, {stale.pk: "interrupted", fresh.pk: "running", manual.pk: "running"})


class SuccessfulRunTests(RunnerTestCase):
    def test_a_scheduled_scan(self):
        watch = make_watch(self.user, self.domain)
        due = watch.next_run_at
        outcome = self.run_one(watch)

        self.assertEqual(outcome.result, "complete")
        scan = outcome.scan
        self.assertEqual((scan.status, scan.trigger), ("complete", TRIGGER_WATCH))
        self.assertTrue(scan.suggest_fix)
        self.assertFalse(scan.verbose)
        self.assertEqual(scan.risk_score, "LOW")
        self.assertEqual(scan.target_url, API)

        watch.refresh_from_db()
        self.assertEqual(watch.consecutive_failures, 0)
        self.assertEqual(watch.last_scan, scan)
        self.assertEqual(watch.last_run_at, scan.completed_at)
        self.assertEqual(watch.next_run_at, due + timedelta(days=30))
        self.assertEqual(watch.last_error, "")

    def test_writes_stay_off(self):
        self.run_one(make_watch(self.user, self.domain))
        kwargs = self.run_scan.call_args.kwargs
        self.assertIs(kwargs["allow_writes"], False)
        self.assertIs(kwargs["suggest_fix"], True)
        self.assertIs(kwargs["verbose"], False)

    def test_the_slot_skips_runs_it_missed(self):
        staff = registered("staff@example.com", is_staff=True)
        domain = domain_for(staff)
        watch = make_watch(staff, domain, due_in=-timedelta(days=17))
        due = watch.next_run_at
        self.run_one(watch)
        watch.refresh_from_db()
        self.assertEqual(watch.next_run_at, due + timedelta(days=21))
        self.assertGreater(watch.next_run_at, timezone.now())

    def test_it_does_not_use_the_daily_allowance(self):
        self.run_one(make_watch(self.user, self.domain))
        self.assertEqual(limits.scans_remaining(self.user)["used"], 0)


class GotWorseTests(RunnerTestCase):
    def earlier_scan(self, severity="PASS", overrides=None):
        raw = build_raw(API, findings(severity, overrides))
        from scanner.report import format_report
        report = format_report(raw)
        return Scan.objects.create(
            user=self.user, target_url=API, status="complete", completed_at=timezone.now() - timedelta(days=30),
            risk_score=report["meta"]["risk_score"], results=report,
        )

    def outcome_for(self, severity="PASS", overrides=None):
        self.run_scan.side_effect = fake_scan(severity, overrides)
        return self.run_one(make_watch(self.user, self.domain))

    def test_a_new_problem(self):
        self.earlier_scan()
        outcome = self.outcome_for(overrides={"API4": "MEDIUM"})
        self.assertTrue(outcome.worse)
        self.assertEqual(outcome.comparison["counts"]["new"], 1)

    def test_a_check_got_worse(self):
        self.earlier_scan(overrides={"API4": "LOW"})
        self.assertTrue(self.outcome_for(overrides={"API4": "MEDIUM"}).worse)

    def test_nothing_changed(self):
        self.earlier_scan(overrides={"API4": "MEDIUM"})
        self.assertFalse(self.outcome_for(overrides={"API4": "MEDIUM"}).worse)

    def test_better_is_not_worse(self):
        self.earlier_scan(overrides={"API4": "MEDIUM"})
        outcome = self.outcome_for()
        self.assertFalse(outcome.worse)
        self.assertEqual(outcome.comparison["counts"]["fixed"], 1)

    def test_the_first_scan_has_nothing_to_compare(self):
        outcome = self.outcome_for(overrides={"API4": "HIGH"})
        self.assertIsNone(outcome.comparison)
        self.assertFalse(outcome.worse)

    def test_got_worse_on_risk_alone(self):
        comparison = {"counts": {"new": 0, "worse": 0}, "risk": {"before": "LOW", "after": "HIGH"}}
        self.assertTrue(runner.got_worse(comparison))
        comparison["risk"] = {"before": "INCOMPLETE", "after": "HIGH"}
        self.assertFalse(runner.got_worse(comparison))


class FailedRunTests(RunnerTestCase):
    def test_a_failed_scan_is_retried_in_an_hour(self):
        self.run_scan.side_effect = ScanFailed("timeout", "The target took too long to respond.")
        watch = make_watch(self.user, self.domain)
        before = timezone.now()
        outcome = self.run_one(watch)

        self.assertEqual((outcome.result, outcome.reason), ("failed", "timeout"))
        self.assertEqual(outcome.scan.status, "failed")
        self.assertEqual(outcome.scan.results["error"]["reason"], "timeout")
        watch.refresh_from_db()
        self.assertEqual(watch.consecutive_failures, 1)
        self.assertEqual(watch.last_error, "timeout")
        self.assertGreaterEqual(watch.next_run_at, before + runner.RETRY_DELAY)
        self.assertFalse(watch.is_paused)

    def test_three_failures_in_a_row_pause_the_watch(self):
        self.run_scan.side_effect = ScanFailed("dns", "We couldn't find that address.")
        watch = make_watch(self.user, self.domain)
        for _ in range(Watch.MAX_FAILURES):
            Watch.objects.filter(pk=watch.pk).update(next_run_at=timezone.now() - timedelta(minutes=1))
            watch.refresh_from_db()
            outcome = self.run_one(watch)
        self.assertEqual((outcome.result, outcome.reason), ("paused", "dns"))
        watch.refresh_from_db()
        self.assertEqual(watch.paused_reason, Watch.PAUSED_FAILURES)
        self.domain.refresh_from_db()
        self.assertTrue(self.domain.verified)

    def test_a_success_clears_the_failures(self):
        self.run_scan.side_effect = ScanFailed("timeout", "slow")
        watch = make_watch(self.user, self.domain)
        self.run_one(watch)
        self.run_scan.side_effect = fake_scan()
        Watch.objects.filter(pk=watch.pk).update(next_run_at=timezone.now() - timedelta(minutes=1))
        watch.refresh_from_db()
        self.assertEqual(self.run_one(watch).result, "complete")
        watch.refresh_from_db()
        self.assertEqual((watch.consecutive_failures, watch.last_error), (0, ""))

    def test_an_engine_crash_is_a_failed_scan(self):
        self.run_scan.side_effect = RuntimeError("bug")
        with self.assertLogs("watch.runner", level="ERROR"):
            outcome = self.run_one(make_watch(self.user, self.domain))
        self.assertEqual((outcome.result, outcome.reason), ("failed", "scan_error"))
        self.assertEqual(outcome.scan.status, "failed")


class RuleATests(RunnerTestCase):
    def due_again(self, watch):
        Watch.objects.filter(pk=watch.pk).update(next_run_at=timezone.now() - timedelta(minutes=1))
        watch.refresh_from_db()

    def test_a_failed_re_check_scans_nothing_and_retries(self):
        self.verify_dns.return_value = False
        watch = make_watch(self.user, self.domain)
        outcome = self.run_one(watch)
        self.assertEqual((outcome.result, outcome.reason), ("unverified", "verification"))
        self.assertFalse(Scan.objects.exists())
        self.run_scan.assert_not_called()
        watch.refresh_from_db()
        self.assertEqual((watch.verification_failures, watch.last_error), (1, "verification"))
        self.domain.refresh_from_db()
        self.assertTrue(self.domain.verified)

    def test_three_failed_re_checks_put_the_domain_back_to_pending(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        other_domain = domain_for(self.user, "other.example.com")
        watch = make_watch(self.user, self.domain)
        sibling = make_watch(self.user, self.domain, f"https://{HOST}/v2", due_in=timedelta(days=3))
        elsewhere = make_watch(self.user, other_domain, "https://other.example.com/v1", due_in=timedelta(days=3))

        self.verify_dns.return_value = False
        for attempt in range(Watch.MAX_FAILURES):
            if attempt:
                self.due_again(watch)
            outcome = self.run_one(watch)

        self.assertEqual((outcome.result, outcome.reason), ("paused", "verification"))
        self.domain.refresh_from_db()
        self.assertFalse(self.domain.verified)
        self.assertIsNone(self.domain.verified_at)
        for w in (watch, sibling):
            w.refresh_from_db()
            self.assertEqual(w.paused_reason, Watch.PAUSED_VERIFICATION)
        elsewhere.refresh_from_db()
        self.assertFalse(elsewhere.is_paused)
        other_domain.refresh_from_db()
        self.assertTrue(other_domain.verified)

    def test_a_pending_domain_blocks_manual_scans_too(self):
        services.domain_lost_verification(self.domain)
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post("/api/scans/create/", {"target_url": API}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_a_passing_re_check_resets_the_count(self):
        watch = make_watch(self.user, self.domain)
        self.verify_dns.return_value = False
        self.run_one(watch)
        self.verify_dns.return_value = True
        self.due_again(watch)
        self.assertEqual(self.run_one(watch).result, "complete")
        watch.refresh_from_db()
        self.assertEqual(watch.verification_failures, 0)

    def test_the_file_method_is_checked_with_the_file(self):
        domain = domain_for(self.user, "files.example.com", method="file")
        self.user.plan = User.PLAN_PRO
        self.user.save()
        self.run_one(make_watch(self.user, domain, "https://files.example.com/v1"))
        self.verify_file.assert_called_once_with("files.example.com", domain.verification_token)
        self.verify_dns.assert_not_called()

    def test_one_re_check_per_domain_per_pass(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        make_watch(self.user, self.domain, API)
        make_watch(self.user, self.domain, f"https://{HOST}/v2")
        summary = runner.run_pass()
        self.assertEqual(summary.count("complete"), 2)
        self.assertEqual(self.verify_dns.call_count, 1)

    def test_verifying_again_restarts_the_watches(self):
        watch = make_watch(self.user, self.domain)
        failing = make_watch(self.user, self.domain, f"https://{HOST}/v2")
        failing.pause(Watch.PAUSED_FAILURES)
        services.domain_lost_verification(self.domain)

        client = APIClient()
        client.force_authenticate(self.user)
        with patch("domains.views.verify_dns", return_value=True):
            response = client.post(f"/api/domains/{self.domain.pk}/verify/")
        self.assertEqual(response.status_code, 200)

        watch.refresh_from_db()
        self.assertFalse(watch.is_paused)
        self.assertEqual((watch.verification_failures, watch.consecutive_failures, watch.last_error), (0, 0, ""))
        self.assertLessEqual(watch.next_run_at, timezone.now())
        failing.refresh_from_db()
        self.assertEqual(failing.paused_reason, Watch.PAUSED_FAILURES)

    def test_resuming_with_the_record_back_verifies_the_domain_again(self):
        watch = make_watch(self.user, self.domain)
        services.domain_lost_verification(self.domain)
        watch.refresh_from_db()
        services.resume_watch(watch)
        watch.refresh_from_db()

        outcome = self.run_one(watch)
        self.assertEqual(outcome.result, "complete")
        self.domain.refresh_from_db()
        self.assertTrue(self.domain.verified)
        self.assertIsNotNone(self.domain.verified_at)


class PassTests(RunnerTestCase):
    def setUp(self):
        super().setUp()
        self.user.plan = User.PLAN_PRO
        self.user.save()
        self.watches = [make_watch(self.user, self.domain, f"https://{HOST}/v{n}", due_in=timedelta(minutes=-10 + n)) for n in range(4)]

    def test_the_budget_stops_new_watches(self):
        ticks = iter([0, 0, 400, 800, 1200])
        summary = runner.run_pass(budget_seconds=600, clock=lambda: next(ticks))
        self.assertEqual(summary.due, 4)
        self.assertEqual(summary.count("complete"), 2)
        self.assertEqual(summary.left, 2)
        left = Watch.objects.filter(pk__in=[w.pk for w in self.watches[2:]])
        self.assertTrue(all(w.next_run_at <= timezone.now() for w in left))

    def test_one_broken_watch_never_stops_the_others(self):
        original = runner.run_watch
        broken = self.watches[0].pk

        def flaky(watch, now, checked):
            if watch.pk == broken:
                raise RuntimeError("bug")
            return original(watch, now, checked)

        with patch.object(runner, "run_watch", side_effect=flaky), self.assertLogs("watch.runner", level="ERROR"):
            summary = runner.run_pass()
        self.assertEqual(summary.count("complete"), 3)
        self.assertEqual(summary.count("failed"), 1)

    def test_a_pass_tidies_left_behind_scans(self):
        stale = Scan.objects.create(user=self.user, target_url=API, status="running", trigger=TRIGGER_WATCH)
        Scan.objects.filter(pk=stale.pk).update(created_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(runner.run_pass().stale, 1)


class PullInTests(RunnerTestCase):
    """A shorter cadence (the beta's weekly free scans, an upgrade to Pro) brings far-off runs forward."""

    def assertAbout(self, when, expected):
        # next_run_from adds a random part of the spread.
        self.assertGreaterEqual(when, expected)
        self.assertLessEqual(when, expected + services.SPREAD)

    def test_a_watch_booked_on_the_old_free_cadence_comes_forward(self):
        start = timezone.now() - timedelta(days=1)
        watch = make_watch(self.user, self.domain, due_in=timedelta(days=29), activated_at=start)
        with self.settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7):
            moved = runner.pull_in(timezone.now())
        watch.refresh_from_db()
        self.assertEqual([w.pk for w in moved], [watch.pk])
        self.assertAbout(watch.next_run_at, start + timedelta(days=7))

    def test_an_upgrade_to_pro_counts_from_the_last_scheduled_scan(self):
        last = timezone.now() - timedelta(days=2)
        watch = make_watch(self.user, self.domain, due_in=timedelta(days=28), last_run_at=last)
        self.assertEqual(runner.pull_in(timezone.now()), [])  # free, 30 days: right where it is
        self.user.plan = User.PLAN_PRO
        self.user.save()
        runner.pull_in(timezone.now())
        watch.refresh_from_db()
        self.assertAbout(watch.next_run_at, last + timedelta(days=7))

    def test_a_watch_already_a_cadence_old_is_due_and_runs_in_the_same_pass(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        watch = make_watch(
            self.user, self.domain, due_in=timedelta(days=10), last_run_at=timezone.now() - timedelta(days=20)
        )
        summary = runner.run_pass()
        self.assertEqual((summary.pulled, summary.due, summary.count("complete")), (1, 1, 1))
        watch.refresh_from_db()
        self.assertEqual(watch.last_scan.trigger, TRIGGER_WATCH)

    def test_left_alone(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        within = make_watch(self.user, self.domain, f"https://{HOST}/a", due_in=timedelta(days=6))
        retry = make_watch(self.user, self.domain, f"https://{HOST}/b", due_in=timedelta(hours=1), consecutive_failures=1)
        paused = make_watch(self.user, self.domain, f"https://{HOST}/c", due_in=timedelta(days=29))
        paused.pause(Watch.PAUSED_FAILURES)
        Watch.objects.filter(pk=paused.pk).update(next_run_at=timezone.now() + timedelta(days=29))
        off = make_watch(self.user, self.domain, f"https://{HOST}/d", due_in=timedelta(days=29), active=False)
        before = {w.pk: Watch.objects.get(pk=w.pk).next_run_at for w in [within, retry, paused, off]}
        self.assertEqual(runner.pull_in(timezone.now()), [])
        after = {pk: Watch.objects.get(pk=pk).next_run_at for pk in before}
        self.assertEqual(before, after)

    def test_never_later_a_longer_cadence_waits_for_its_next_run(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        watch = make_watch(self.user, self.domain, due_in=timedelta(days=5))
        self.user.plan = User.PLAN_FREE
        self.user.save()
        self.assertEqual(runner.pull_in(timezone.now()), [])
        watch.refresh_from_db()
        self.assertLess(watch.next_run_at, timezone.now() + timedelta(days=5, minutes=1))

    def test_once_only(self):
        make_watch(self.user, self.domain, due_in=timedelta(days=29), activated_at=timezone.now())
        with self.settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7):
            self.assertEqual(len(runner.pull_in(timezone.now())), 1)
            self.assertEqual(runner.pull_in(timezone.now()), [])

    def test_a_dry_run_changes_nothing(self):
        watch = make_watch(self.user, self.domain, due_in=timedelta(days=29))
        booked = Watch.objects.get(pk=watch.pk).next_run_at
        with self.settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7):
            self.assertEqual(len(runner.pull_in(timezone.now(), dry_run=True)), 1)
        self.assertEqual(Watch.objects.get(pk=watch.pk).next_run_at, booked)

    def test_a_watch_changed_meanwhile_keeps_its_new_booking(self):
        watch = make_watch(self.user, self.domain, due_in=timedelta(days=29))
        soon = timezone.now() + timedelta(days=3)
        original = Watch.objects.filter

        def stale_read(*args, **kwargs):
            queryset = original(*args, **kwargs)
            if "next_run_at" in kwargs and "pk" in kwargs:
                # Someone rebooked it between the read and the update.
                Watch.objects.all().update(next_run_at=soon)
            return queryset

        with self.settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7), patch.object(Watch.objects, "filter", side_effect=stale_read):
            self.assertEqual(runner.pull_in(timezone.now()), [])
        watch.refresh_from_db()
        self.assertEqual(watch.next_run_at, soon)

    def test_a_problem_here_never_stops_the_pass(self):
        make_watch(self.user, self.domain)
        with patch.object(runner, "pull_in", side_effect=RuntimeError("bug")), self.assertLogs("watch.runner", level="ERROR"):
            summary = runner.run_pass()
        self.assertEqual((summary.pulled, summary.count("complete")), (0, 1))


class CommandTests(RunnerTestCase):
    def call(self, *args):
        out = StringIO()
        call_command("run_watches", *args, stdout=out)
        return out.getvalue()

    def test_a_run(self):
        make_watch(self.user, self.domain, f"{API}?api_key=secret123")
        output = self.call()
        self.assertIn("complete, risk LOW", output)
        self.assertIn("run_watches: 1 due, 1 complete (0 worse)", output)
        self.assertNotIn("secret123", output)

    def test_a_dry_run_changes_nothing(self):
        watch = make_watch(self.user, self.domain, f"{API}?token=abc")
        output = self.call("--dry-run")
        self.assertIn("1 watch(es) due", output)
        self.assertIn(f"watch {watch.pk} {HOST}/v1", output)
        self.assertNotIn("abc", output)
        self.assertFalse(Scan.objects.exists())
        self.run_scan.assert_not_called()

    def test_failures_and_pauses_are_described(self):
        self.verify_dns.return_value = False
        make_watch(self.user, self.domain)
        self.assertIn("verification failed (1 of 3), retry in 1 hour", self.call())

    def test_the_first_line_gives_the_cadences(self):
        with self.settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7):
            first = self.call().splitlines()[0]
        self.assertEqual(first, "shovl watch: free plan every 7 days, pro every 7 days")
        self.assertIn("free plan every 30 days", self.call("--dry-run"))

    def test_watches_brought_forward_are_counted(self):
        make_watch(self.user, self.domain, due_in=timedelta(days=29))
        with self.settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7):
            dry = self.call("--dry-run")
            self.assertIn("1 watch(es) would come forward", dry)
            self.assertIn("1 brought forward", self.call())

    def test_a_budget_below_one_is_refused(self):
        with self.assertRaises(CommandError):
            self.call("--budget", "0")
