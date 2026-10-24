"""
The rules in watch/services.py: starting a watch when a scan completes, which watches fit the
plan, the badge a report shows, and watching, swapping, turning off and resuming.

Run with:  DJANGO_DEBUG=1 python manage.py test watch
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts import plans
from domains.models import Domain
from scans.models import TRIGGER_WATCH, Scan
from watch import services
from watch.models import Watch

User = get_user_model()

PASSWORD = "correct horse battery staple"
HOST = "api.example.com"
API = f"https://{HOST}/v1"
API2 = f"https://{HOST}/v2"
API3 = f"https://{HOST}/v3"
PRACTICE = "https://postman-echo.com/get"


def registered(email="real@example.com", **fields):
    return User.objects.create_user(email, PASSWORD, tos_agreed=True, **fields)


def domain_for(user, hostname=HOST, verified=True):
    return Domain.objects.create(
        user=user,
        hostname=hostname,
        verified=verified,
        verified_at=timezone.now() if verified else None,
    )


def scan_of(user, url=API, status="complete", trigger="manual", when=None):
    when = when or timezone.now()
    scan = Scan.objects.create(user=user, target_url=url, status=status, trigger=trigger)
    Scan.objects.filter(pk=scan.pk).update(created_at=when, completed_at=when if status == "complete" else None)
    scan.refresh_from_db()
    return scan


def no_spread():
    return patch.object(services, "_spread", return_value=timedelta(0))


class WatchAfterScanTests(TestCase):
    def setUp(self):
        self.user = registered()
        self.domain = domain_for(self.user)

    def test_a_scan_of_your_own_verified_domain_starts_a_watch(self):
        scan = scan_of(self.user)
        watch = services.watch_after_scan(scan)
        self.assertIsNotNone(watch)
        self.assertEqual(watch.user, self.user)
        self.assertEqual(watch.domain, self.domain)
        self.assertEqual(watch.target_url, API)
        self.assertTrue(watch.active)

    def test_the_first_run_is_one_cadence_after_the_scan_plus_a_spread(self):
        scan = scan_of(self.user)
        watch = services.watch_after_scan(scan)
        earliest = scan.completed_at + timedelta(days=30)
        self.assertGreaterEqual(watch.next_run_at, earliest)
        self.assertLessEqual(watch.next_run_at, earliest + services.SPREAD)

    @override_settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7)
    def test_the_beta_cadence(self):
        scan = scan_of(self.user)
        with no_spread():
            watch = services.watch_after_scan(scan)
        self.assertEqual(watch.next_run_at, scan.completed_at + timedelta(days=7))

    def test_nothing_for_a_practice_target(self):
        self.assertIsNone(services.watch_after_scan(scan_of(self.user, PRACTICE)))
        self.assertFalse(Watch.objects.exists())

    def test_nothing_for_an_unverified_domain(self):
        domain_for(self.user, "pending.example.com", verified=False)
        self.assertIsNone(services.watch_after_scan(scan_of(self.user, "https://pending.example.com/v1")))

    def test_nothing_for_someone_elses_domain(self):
        other = registered("other@example.com")
        self.assertIsNone(services.watch_after_scan(scan_of(other, API)))

    def test_nothing_for_a_guest(self):
        guest = User.objects.create_guest(tos_agreed=True)
        self.assertIsNone(services.watch_after_scan(scan_of(guest, PRACTICE)))

    def test_nothing_for_a_scan_that_did_not_complete(self):
        for status in ("failed", "interrupted", "stopped", "running"):
            with self.subTest(status=status):
                self.assertIsNone(services.watch_after_scan(scan_of(self.user, status=status)))

    def test_nothing_for_a_scheduled_scan(self):
        self.assertIsNone(services.watch_after_scan(scan_of(self.user, trigger=TRIGGER_WATCH)))

    def test_nothing_while_the_account_switch_is_off(self):
        self.user.watch_enabled = False
        self.user.save()
        self.assertIsNone(services.watch_after_scan(scan_of(self.user)))

    def test_free_watches_the_first_api_only(self):
        first = services.watch_after_scan(scan_of(self.user, API))
        self.assertIsNone(services.watch_after_scan(scan_of(self.user, API2)))
        self.assertEqual(list(Watch.objects.all()), [first])

    def test_pro_watches_five(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        urls = [f"https://{HOST}/v{n}" for n in range(1, 7)]
        results = [services.watch_after_scan(scan_of(self.user, url)) for url in urls]
        self.assertTrue(all(results[:5]))
        self.assertIsNone(results[5])
        self.assertEqual(Watch.objects.count(), 5)

    def test_staff_has_no_limit(self):
        staff = registered("staff@example.com", is_staff=True)
        domain_for(staff)
        for n in range(1, 8):
            services.watch_after_scan(scan_of(staff, f"https://{HOST}/v{n}"))
        self.assertEqual(Watch.objects.filter(user=staff).count(), 7)

    def test_the_same_api_again_keeps_one_watch_and_follows_the_newest_address(self):
        first = services.watch_after_scan(scan_of(self.user, "http://api.example.com/v1"))
        again = services.watch_after_scan(scan_of(self.user, "https://API.example.com/v1/"))
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(Watch.objects.count(), 1)
        first.refresh_from_db()
        self.assertEqual(first.target_url, "https://API.example.com/v1/")

    def test_an_api_turned_off_stays_off(self):
        watch = services.watch_after_scan(scan_of(self.user))
        services.set_active(self.user, watch, False)
        services.watch_after_scan(scan_of(self.user))
        watch.refresh_from_db()
        self.assertFalse(watch.active)


class InPlanTests(TestCase):
    def setUp(self):
        self.user = registered(plan=User.PLAN_PRO)
        domain = domain_for(self.user)
        now = timezone.now()
        self.watches = [
            Watch.objects.create(user=self.user, domain=domain, target_url=f"https://{HOST}/v{n}", activated_at=now - timedelta(days=10 - n))
            for n in range(1, 4)
        ]

    def test_pro_fits_all_three(self):
        self.assertEqual(services.in_plan_ids(self.user), {w.pk for w in self.watches})

    def test_a_failed_payment_keeps_only_the_first(self):
        with patch.object(plans, "pro_is_paid", return_value=False):
            self.assertEqual(services.in_plan_ids(self.user), {self.watches[0].pk})

    def test_turned_off_watches_take_no_slot(self):
        self.watches[0].active = False
        self.watches[0].save()
        self.user.plan = User.PLAN_FREE
        self.assertEqual(services.in_plan_ids(self.user), {self.watches[1].pk})

    def test_has_room(self):
        self.assertTrue(services.has_room(self.user))
        self.user.plan = User.PLAN_FREE
        self.assertFalse(services.has_room(self.user))


class ScanWatchStateTests(TestCase):
    def setUp(self):
        self.user = registered()
        self.domain = domain_for(self.user)

    def state(self, scan):
        return services.scan_watch_state(scan)

    def test_watching(self):
        scan = scan_of(self.user)
        watch = services.watch_after_scan(scan)
        state = self.state(scan)
        self.assertEqual(state["status"], "watching")
        self.assertIsNone(state["reason"])
        self.assertIsNone(state["action"])
        self.assertEqual(state["next_run_at"], watch.next_run_at)
        self.assertEqual(state["cadence_days"], 30)
        self.assertEqual(state["watch_slots"], 1)
        self.assertEqual(state["watch_id"], watch.pk)

    def test_a_scheduled_scan_shows_the_same_badge(self):
        services.watch_after_scan(scan_of(self.user))
        self.assertEqual(self.state(scan_of(self.user, trigger=TRIGGER_WATCH))["status"], "watching")

    def test_nothing_for_practice_targets_and_guests(self):
        self.assertIsNone(self.state(scan_of(self.user, PRACTICE)))
        guest = User.objects.create_guest(tos_agreed=True)
        self.assertIsNone(self.state(scan_of(guest, PRACTICE)))

    def test_not_started_offers_watch(self):
        state = self.state(scan_of(self.user))
        self.assertEqual((state["status"], state["reason"], state["action"]), ("not_watched", "not_started", "watch"))
        self.assertIsNone(state["watch_id"])
        self.assertIsNone(state["next_run_at"])

    def test_free_plan_full_offers_swap(self):
        services.watch_after_scan(scan_of(self.user, API))
        state = self.state(scan_of(self.user, API2))
        self.assertEqual((state["status"], state["reason"], state["action"]), ("not_watched", "plan_full", "swap"))

    def test_pro_plan_full_sends_to_settings(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        for n in range(1, 6):
            services.watch_after_scan(scan_of(self.user, f"https://{HOST}/v{n}"))
        state = self.state(scan_of(self.user, f"https://{HOST}/v6"))
        self.assertEqual((state["reason"], state["action"]), ("plan_full", "settings"))
        self.assertEqual(state["watch_slots"], 5)

    def test_account_switch_off(self):
        services.watch_after_scan(scan_of(self.user))
        self.user.watch_enabled = False
        self.user.save()
        state = self.state(scan_of(self.user))
        self.assertEqual((state["status"], state["reason"], state["action"]), ("off", "account_off", "settings"))
        self.assertIsNone(state["next_run_at"])

    def test_account_switch_off_without_a_watch(self):
        self.user.watch_enabled = False
        self.user.save()
        state = self.state(scan_of(self.user))
        self.assertEqual((state["status"], state["reason"]), ("off", "account_off"))

    def test_paused_offers_resume(self):
        watch = services.watch_after_scan(scan_of(self.user))
        watch.pause(Watch.PAUSED_VERIFICATION)
        state = self.state(scan_of(self.user))
        self.assertEqual((state["status"], state["reason"], state["action"]), ("paused", "verification", "resume"))

    def test_turned_off_with_room_offers_watch(self):
        watch = services.watch_after_scan(scan_of(self.user))
        services.set_active(self.user, watch, False)
        state = self.state(scan_of(self.user))
        self.assertEqual((state["status"], state["reason"], state["action"]), ("off", "turned_off", "watch"))

    def test_turned_off_without_room_offers_swap(self):
        first = services.watch_after_scan(scan_of(self.user, API))
        services.set_active(self.user, first, False)
        services.watch_after_scan(scan_of(self.user, API2))
        state = self.state(scan_of(self.user, API))
        self.assertEqual((state["status"], state["reason"], state["action"]), ("off", "turned_off", "swap"))

    def test_over_the_plan_after_a_failed_payment(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        services.watch_after_scan(scan_of(self.user, API))
        services.watch_after_scan(scan_of(self.user, API2))
        with patch.object(plans, "pro_is_paid", return_value=False):
            self.assertEqual(self.state(scan_of(self.user, API))["status"], "watching")
            state = self.state(scan_of(self.user, API2))
        self.assertEqual((state["status"], state["reason"], state["action"]), ("not_watched", "over_plan", "swap"))

    def test_unverified(self):
        domain_for(self.user, "pending.example.com", verified=False)
        state = self.state(scan_of(self.user, "https://pending.example.com/v1"))
        self.assertEqual((state["status"], state["reason"], state["action"]), ("not_watched", "unverified", None))


class WatchScanTests(TestCase):
    def setUp(self):
        self.user = registered()
        self.domain = domain_for(self.user)

    def test_starts_a_watch(self):
        scan = scan_of(self.user)
        with no_spread():
            watch, changed = services.watch_scan(self.user, scan)
        self.assertTrue(changed)
        self.assertTrue(watch.active)
        self.assertEqual(watch.next_run_at, scan.completed_at + timedelta(days=30))

    def test_already_watching_changes_nothing(self):
        first = services.watch_after_scan(scan_of(self.user))
        watch, changed = services.watch_scan(self.user, scan_of(self.user))
        self.assertFalse(changed)
        self.assertEqual(watch.pk, first.pk)

    def test_a_full_plan_is_refused_without_instead(self):
        first = services.watch_after_scan(scan_of(self.user, API))
        with self.assertRaises(services.WatchRefused) as refused:
            services.watch_scan(self.user, scan_of(self.user, API2))
        self.assertEqual(refused.exception.code, "plan_full")
        self.assertEqual(refused.exception.http_status, 409)
        self.assertTrue(refused.exception.extra["can_swap"])
        first.refresh_from_db()
        self.assertTrue(first.active)

    def test_watch_this_one_instead(self):
        first = services.watch_after_scan(scan_of(self.user, API))
        watch, changed = services.watch_scan(self.user, scan_of(self.user, API2), instead=True)
        self.assertTrue(changed)
        first.refresh_from_db()
        self.assertFalse(first.active)
        self.assertEqual(services.in_plan_ids(self.user), {watch.pk})

    def test_swapping_back_turns_the_first_one_on_again(self):
        first = services.watch_after_scan(scan_of(self.user, API))
        second, _ = services.watch_scan(self.user, scan_of(self.user, API2), instead=True)
        back, changed = services.watch_scan(self.user, scan_of(self.user, API), instead=True)
        self.assertTrue(changed)
        self.assertEqual(back.pk, first.pk)
        second.refresh_from_db()
        self.assertFalse(second.active)
        self.assertEqual(Watch.objects.count(), 2)

    def test_pro_cannot_swap(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        for n in range(1, 6):
            services.watch_after_scan(scan_of(self.user, f"https://{HOST}/v{n}"))
        with self.assertRaises(services.WatchRefused) as refused:
            services.watch_scan(self.user, scan_of(self.user, f"https://{HOST}/v6"), instead=True)
        self.assertFalse(refused.exception.extra["can_swap"])
        self.assertEqual(Watch.objects.filter(active=True).count(), 5)

    def test_instead_after_a_failed_payment_keeps_only_this_one(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        for url in (API, API2, API3):
            services.watch_after_scan(scan_of(self.user, url))
        with patch.object(plans, "pro_is_paid", return_value=False):
            watch, _ = services.watch_scan(self.user, scan_of(self.user, API3), instead=True)
            self.assertEqual(services.in_plan_ids(self.user), {watch.pk})
        self.assertEqual(list(Watch.objects.filter(active=True)), [watch])

    def test_no_extra_scan_from_an_old_report(self):
        # The API was scanned on schedule yesterday; watching it again from a report a month old
        # must not make it due now.
        first = services.watch_after_scan(scan_of(self.user, API))
        first.last_run_at = timezone.now() - timedelta(days=1)
        first.save()
        services.watch_scan(self.user, scan_of(self.user, API2), instead=True)
        old_report = scan_of(self.user, API, when=timezone.now() - timedelta(days=30))
        with no_spread():
            back, _ = services.watch_scan(self.user, old_report, instead=True)
        self.assertEqual(back.next_run_at, first.last_run_at + timedelta(days=30))

    def test_refusals(self):
        with self.assertRaises(services.WatchRefused) as refused:
            services.watch_scan(self.user, scan_of(self.user, PRACTICE))
        self.assertEqual(refused.exception.code, "practice_target")

        domain_for(self.user, "pending.example.com", verified=False)
        with self.assertRaises(services.WatchRefused) as refused:
            services.watch_scan(self.user, scan_of(self.user, "https://pending.example.com/v1"))
        self.assertEqual(refused.exception.code, "domain_not_verified")

        guest = User.objects.create_guest(tos_agreed=True)
        with self.assertRaises(services.WatchRefused) as refused:
            services.watch_scan(guest, scan_of(guest, PRACTICE))
        self.assertEqual(refused.exception.code, "registration_required")
        self.assertFalse(Watch.objects.exists())


class SetActiveAndResumeTests(TestCase):
    def setUp(self):
        self.user = registered()
        domain_for(self.user)
        self.watch = services.watch_after_scan(scan_of(self.user, API))

    def test_off_and_on(self):
        services.set_active(self.user, self.watch, False)
        self.watch.refresh_from_db()
        self.assertFalse(self.watch.active)
        services.set_active(self.user, self.watch, True)
        self.watch.refresh_from_db()
        self.assertTrue(self.watch.active)

    def test_on_without_room_is_refused(self):
        services.set_active(self.user, self.watch, False)
        services.watch_after_scan(scan_of(self.user, API2))
        with self.assertRaises(services.WatchRefused) as refused:
            services.set_active(self.user, self.watch, True)
        self.assertEqual(refused.exception.code, "plan_full")
        self.watch.refresh_from_db()
        self.assertFalse(self.watch.active)

    def test_back_on_is_scheduled_from_the_last_run(self):
        last = timezone.now() - timedelta(days=3)
        self.watch.last_run_at = last
        self.watch.save()
        services.set_active(self.user, self.watch, False)
        with no_spread():
            services.set_active(self.user, self.watch, True)
        self.watch.refresh_from_db()
        self.assertEqual(self.watch.next_run_at, last + timedelta(days=30))

    def test_back_on_goes_last_in_the_plan_order(self):
        before = self.watch.activated_at
        services.set_active(self.user, self.watch, False)
        services.set_active(self.user, self.watch, True)
        self.watch.refresh_from_db()
        self.assertGreater(self.watch.activated_at, before)

    def test_resume(self):
        self.watch.consecutive_failures = Watch.MAX_FAILURES
        self.watch.save()
        self.watch.pause(Watch.PAUSED_FAILURES)
        services.resume_watch(self.watch)
        self.watch.refresh_from_db()
        self.assertFalse(self.watch.is_paused)
        self.assertEqual(self.watch.consecutive_failures, 0)

    def test_resume_leaves_a_running_watch_alone(self):
        due = self.watch.next_run_at
        services.resume_watch(self.watch)
        self.watch.refresh_from_db()
        self.assertEqual(self.watch.next_run_at, due)
