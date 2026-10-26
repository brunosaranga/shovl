"""
The bell: news (the announcement, "now watching", alerts from the runner), needs action
(pending domains, rule A, paused watches), the badge and mute, the endpoints, removing
pending domains (the unverified cache) and the two admin pages.

Nothing here touches the network: the engine and the verification checks are replaced.

Run with:  DJANGO_DEBUG=1 python manage.py test notifications
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from domains.models import Domain
from notifications import services as bell
from notifications.models import Notification
from scanner.engine import CHECK_INFO, CHECKS, build_raw
from scanner.report import format_report
from scans.models import Scan
from watch import runner, services
from watch.models import Watch

User = get_user_model()

PASSWORD = "correct horse battery staple"
HOST = "api.example.com"
API = f"https://{HOST}/v1"
API2 = f"https://{HOST}/v2"
BELL = "/api/notifications/"


def registered(email="real@example.com", **fields):
    return User.objects.create_user(email, PASSWORD, tos_agreed=True, **fields)


def domain_for(user, hostname=HOST, verified=True):
    return Domain.objects.create(user=user, hostname=hostname, verified=verified, verified_at=timezone.now() if verified else None)


def scan_of(user, url=API):
    return Scan.objects.create(user=user, target_url=url, status="complete", completed_at=timezone.now())


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def report(overrides=None):
    overrides = overrides or {}
    findings = []
    for path in CHECKS:
        name, check_id = CHECK_INFO[path]
        findings.append({"check": name, "id": check_id, "severity": overrides.get(check_id, "PASS"), "detail": ["x"]})
    return format_report(build_raw(API, findings))


def fake_scan(overrides=None):
    def run(target_url, **kwargs):
        findings = report(overrides)["findings"]
        return build_raw(target_url, findings, False, True)
    return run


class AnnouncementTests(TestCase):
    def setUp(self):
        self.user = registered()
        domain_for(self.user)

    def test_the_first_watch_brings_the_announcement_once(self):
        services.watch_after_scan(scan_of(self.user))
        item = Notification.objects.get()
        self.assertEqual(item.kind, Notification.KIND_WATCH_ON)
        self.assertEqual(item.title, f"murindzi is on for {HOST}/v1")
        self.assertIn("tells you when something gets worse", item.summary)
        self.assertIn("every 30 days", item.summary)
        self.assertIn("settings", item.summary)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.watch_intro_at)

    def test_later_automatic_watches_say_now_watching(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        services.watch_after_scan(scan_of(self.user, API))
        services.watch_after_scan(scan_of(self.user, API2))
        kinds = list(Notification.objects.order_by("pk").values_list("kind", flat=True))
        self.assertEqual(kinds, [Notification.KIND_WATCH_ON, Notification.KIND_NOW_WATCHING])
        self.assertEqual(Notification.objects.order_by("pk").last().title, f"now watching {HOST}/v2")

    def test_a_watch_you_start_yourself_says_nothing_after_the_first(self):
        services.watch_after_scan(scan_of(self.user, API))
        services.watch_scan(self.user, scan_of(self.user, API2), instead=True)
        self.assertEqual(Notification.objects.count(), 1)

    def test_your_first_watch_by_hand_still_brings_the_announcement(self):
        services.watch_scan(self.user, scan_of(self.user))
        self.assertEqual(Notification.objects.get().kind, Notification.KIND_WATCH_ON)

    def test_the_announcement_never_repeats(self):
        watch = services.watch_after_scan(scan_of(self.user))
        watch.delete()
        services.watch_after_scan(scan_of(self.user))
        self.assertEqual(Notification.objects.filter(kind=Notification.KIND_WATCH_ON).count(), 1)

    def test_a_query_string_never_reaches_the_title(self):
        services.watch_after_scan(scan_of(self.user, f"{API}?api_key=secret"))
        self.assertNotIn("secret", Notification.objects.get().title)

    def test_an_existing_watch_brings_nothing(self):
        services.watch_after_scan(scan_of(self.user))
        services.watch_after_scan(scan_of(self.user))
        self.assertEqual(Notification.objects.count(), 1)


class AlertTests(TestCase):
    def setUp(self):
        self.user = registered()
        self.domain = domain_for(self.user)
        self.user.watch_intro_at = timezone.now()
        self.user.save()
        patcher = patch.object(runner, "verify_dns", return_value=True)
        patcher.start()
        self.addCleanup(patch.stopall)
        earlier = report()
        Scan.objects.create(
            user=self.user, target_url=API, status="complete", completed_at=timezone.now() - timedelta(days=30),
            risk_score=earlier["meta"]["risk_score"], results=earlier,
        )
        self.watch = Watch.objects.create(user=self.user, domain=self.domain, target_url=API, next_run_at=timezone.now())

    def run_with(self, overrides=None):
        with patch.object(runner, "run_scan", side_effect=fake_scan(overrides)):
            return runner.run_pass()

    def test_worse_means_an_alert(self):
        summary = self.run_with({"API4": "MEDIUM", "API2": "HIGH"})
        alert = Notification.objects.get(kind=Notification.KIND_ALERT)
        self.assertEqual(alert.title, f"{HOST}/v1 got worse")
        self.assertIn("Risk LOW → HIGH.", alert.summary)
        self.assertIn("New problem:", alert.summary)
        self.assertEqual(alert.scan, summary.outcomes[0].scan)
        self.assertEqual(alert.watch, self.watch)
        self.assertEqual(alert.data["risk"], {"before": "LOW", "after": "HIGH"})
        self.assertEqual({c["id"] for c in alert.data["changes"]}, {"API4", "API2"})
        self.assertEqual(alert.data["counts"]["new"], 2)

    def test_the_same_or_better_brings_nothing(self):
        self.run_with()
        self.assertFalse(Notification.objects.exists())

    def test_a_failed_run_brings_nothing(self):
        from scanner.engine import ScanFailed
        with patch.object(runner, "run_scan", side_effect=ScanFailed("timeout", "slow")):
            runner.run_pass()
        self.assertFalse(Notification.objects.exists())

    def test_a_notification_problem_never_breaks_the_pass(self):
        with patch.object(runner, "record_outcome", side_effect=RuntimeError("bug")), \
                self.assertLogs("watch.runner", level="ERROR"):
            summary = self.run_with({"API4": "MEDIUM"})
        self.assertEqual(summary.count("complete"), 1)
        self.watch.refresh_from_db()
        self.assertEqual(self.watch.consecutive_failures, 0)

    def test_alerts_land_even_when_muted(self):
        self.user.notifications_muted = True
        self.user.save()
        self.run_with({"API4": "MEDIUM"})
        self.assertEqual(Notification.objects.filter(kind=Notification.KIND_ALERT).count(), 1)

    def test_alert_summary_lists_at_most_three_names(self):
        checks = [{"check": f"Check {n}", "change": "new"} for n in range(5)]
        text = bell.alert_summary({"risk": {"before": "LOW", "after": "LOW"}, "checks": checks})
        self.assertEqual(text, "New problem: Check 0, Check 1, Check 2, 2 more.")


class NeedsActionTests(TestCase):
    def setUp(self):
        self.user = registered(plan=User.PLAN_PRO)
        self.domain = domain_for(self.user)

    def kinds(self):
        return [item["kind"] for item in bell.needs_action(self.user)]

    def test_nothing_to_do(self):
        Watch.objects.create(user=self.user, domain=self.domain, target_url=API)
        self.assertEqual(bell.needs_action(self.user), [])

    def test_a_pending_domain(self):
        pending = domain_for(self.user, "pending.example.com", verified=False)
        [item] = bell.needs_action(self.user)
        self.assertEqual(item["kind"], "domain_pending")
        self.assertEqual(item["title"], "unverified domain: pending.example.com")
        self.assertEqual(item["actions"], ["verify", "remove"])
        self.assertEqual(item["domain_id"], pending.pk)
        self.assertEqual(item["key"], f"domain:{pending.pk}")

    def test_rule_a_is_one_item_per_domain(self):
        Watch.objects.create(user=self.user, domain=self.domain, target_url=API)
        Watch.objects.create(user=self.user, domain=self.domain, target_url=API2)
        services.domain_lost_verification(self.domain)
        [item] = bell.needs_action(self.user)
        self.assertEqual(item["kind"], "domain_lost_verification")
        self.assertEqual(item["title"], f"verification no longer passes: {HOST}")
        self.assertIn("its 2 watches are paused", item["summary"])
        self.assertEqual(len(item["watch_ids"]), 2)

    def test_a_watch_paused_after_failed_runs(self):
        watch = Watch.objects.create(user=self.user, domain=self.domain, target_url=API, last_error="timeout")
        watch.pause(Watch.PAUSED_FAILURES)
        [item] = bell.needs_action(self.user)
        self.assertEqual(item["kind"], "watch_paused")
        self.assertEqual(item["actions"], ["resume"])
        self.assertIn("The target took too long to respond.", item["summary"])
        self.assertEqual(item["watch_id"], watch.pk)

    def test_most_urgent_first(self):
        domain_for(self.user, "pending.example.com", verified=False)
        other = domain_for(self.user, "other.example.com")
        failing = Watch.objects.create(user=self.user, domain=other, target_url="https://other.example.com/")
        failing.pause(Watch.PAUSED_FAILURES)
        Watch.objects.create(user=self.user, domain=self.domain, target_url=API)
        services.domain_lost_verification(self.domain)
        self.assertEqual(self.kinds(), ["domain_lost_verification", "watch_paused", "domain_pending"])

    def test_turned_off_watches_and_the_account_switch(self):
        watch = Watch.objects.create(user=self.user, domain=self.domain, target_url=API)
        watch.pause(Watch.PAUSED_FAILURES)
        self.user.watch_enabled = False
        self.user.save()
        self.assertEqual(self.kinds(), [])
        self.user.watch_enabled = True
        self.user.save()
        watch.active = False
        watch.save()
        self.assertEqual(self.kinds(), [])

    def test_verifying_again_clears_the_item(self):
        Watch.objects.create(user=self.user, domain=self.domain, target_url=API)
        services.domain_lost_verification(self.domain)
        self.domain.verified = True
        self.domain.save()
        services.domain_verified_again(self.domain)
        self.assertEqual(self.kinds(), [])

    def test_guests_have_nothing(self):
        guest = User.objects.create_guest(tos_agreed=True)
        self.assertEqual(bell.needs_action(guest), [])


class BellEndpointTests(TestCase):
    def setUp(self):
        self.user = registered()
        domain_for(self.user)
        self.client = signed_in(self.user)

    def news(self, count):
        return [Notification.objects.create(user=self.user, kind=Notification.KIND_NOW_WATCHING, title=f"n{n}") for n in range(count)]

    def test_the_bell(self):
        services.watch_after_scan(scan_of(self.user))
        domain_for(self.user, "pending.example.com", verified=False)
        data = self.client.get(BELL).data
        self.assertEqual(data["badge"], 2)
        self.assertFalse(data["muted"])
        self.assertEqual(data["news_unread"], 1)
        self.assertEqual([n["kind"] for n in data["news"]], [Notification.KIND_WATCH_ON])
        self.assertFalse(data["news"][0]["read"])
        self.assertEqual([i["kind"] for i in data["needs_action"]], ["domain_pending"])
        self.assertFalse(data["has_more"])

    def test_mute_quiets_news_only(self):
        self.news(2)
        domain_for(self.user, "pending.example.com", verified=False)
        self.client.patch("/api/accounts/me/", {"notifications_muted": True}, format="json")
        data = self.client.get(BELL).data
        self.assertTrue(data["muted"])
        self.assertEqual(data["badge"], 1)
        self.assertEqual(data["news_unread"], 2)
        self.assertEqual(len(data["news"]), 2)

    def test_read_one_and_read_all(self):
        first, second, third = self.news(3)
        response = self.client.post(f"{BELL}{first.pk}/read/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["read"])
        self.assertEqual(self.client.get(BELL).data["badge"], 2)
        again = self.client.post(f"{BELL}{first.pk}/read/")
        self.assertEqual(again.status_code, 200)
        response = self.client.post(f"{BELL}read-all/")
        self.assertEqual(response.data, {"marked": 2})
        self.assertEqual(self.client.get(BELL).data["badge"], 0)

    def test_pages_of_news(self):
        items = self.news(35)
        first = self.client.get(BELL).data
        self.assertEqual(len(first["news"]), 30)
        self.assertTrue(first["has_more"])
        self.assertEqual(first["news"][0]["id"], items[-1].pk)
        older = self.client.get(BELL, {"before": first["news"][-1]["id"]}).data
        self.assertEqual(len(older["news"]), 5)
        self.assertFalse(older["has_more"])
        self.assertEqual(self.client.get(BELL, {"before": "abc"}).status_code, 400)

    def test_yours_only(self):
        other = registered("other@example.com")
        theirs = Notification.objects.create(user=other, kind=Notification.KIND_ALERT, title="theirs")
        self.assertEqual(self.client.get(BELL).data["news"], [])
        self.assertEqual(self.client.post(f"{BELL}{theirs.pk}/read/").status_code, 404)
        self.client.post(f"{BELL}read-all/")
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_guests_get_an_empty_bell_and_strangers_a_401(self):
        guest = User.objects.create_guest(tos_agreed=True)
        data = signed_in(guest).get(BELL).data
        self.assertEqual((data["badge"], data["needs_action"], data["news"]), (0, [], []))
        self.assertEqual(APIClient().get(BELL).status_code, 401)


class UnverifiedCacheTests(TestCase):
    def setUp(self):
        self.user = registered()
        self.verified = domain_for(self.user)
        self.client = signed_in(self.user)

    def test_remove_one_pending_domain(self):
        pending = domain_for(self.user, "pending.example.com", verified=False)
        response = self.client.delete(f"/api/domains/{pending.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Domain.objects.filter(pk=pending.pk).exists())

    def test_a_verified_domain_stays(self):
        response = self.client.delete(f"/api/domains/{self.verified.pk}/")
        self.assertEqual((response.status_code, response.data["code"]), (409, "domain_verified"))
        self.assertTrue(Domain.objects.filter(pk=self.verified.pk).exists())

    def test_empty_the_cache(self):
        domain_for(self.user, "a.example.com", verified=False)
        domain_for(self.user, "b.example.com", verified=False)
        other = registered("other@example.com")
        theirs = domain_for(other, "c.example.com", verified=False)
        response = self.client.delete("/api/domains/pending/")
        self.assertEqual(response.data, {"removed": 2})
        self.assertEqual(list(Domain.objects.filter(user=self.user)), [self.verified])
        self.assertTrue(Domain.objects.filter(pk=theirs.pk).exists())

    def test_removing_a_domain_that_lost_verification_removes_its_watches(self):
        Watch.objects.create(user=self.user, domain=self.verified, target_url=API)
        services.domain_lost_verification(self.verified)
        self.assertEqual(self.client.delete(f"/api/domains/{self.verified.pk}/").status_code, 204)
        self.assertFalse(Watch.objects.exists())

    def test_someone_elses_domain(self):
        other = registered("other@example.com")
        theirs = domain_for(other, "c.example.com", verified=False)
        self.assertEqual(self.client.delete(f"/api/domains/{theirs.pk}/").status_code, 404)
        self.assertTrue(Domain.objects.filter(pk=theirs.pk).exists())

    def test_guests(self):
        guest = User.objects.create_guest(tos_agreed=True)
        response = signed_in(guest).delete("/api/domains/pending/")
        self.assertEqual((response.status_code, response.data["code"]), (403, "registration_required"))


class AdminPageTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("boss@example.com", PASSWORD))
        user = registered()
        domain_for(user)
        Notification.objects.create(user=user, kind=Notification.KIND_ALERT, title="api got worse")

    def test_domains_and_notifications(self):
        for name in ("admin:domains_domain_changelist", "admin:notifications_notification_changelist"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertContains(self.client.get(reverse("admin:domains_domain_changelist")), HOST)


class RenameMigrationTests(TestCase):
    """notifications/migrations/0004: announcements stored under an old name now say murindzi."""

    def rewrite(self):
        import importlib

        from django.apps import apps

        migration = importlib.import_module("notifications.migrations.0004_rewrite_watch_on_text")
        migration.forwards(apps, None)

    def make(self, kind, title, summary=""):
        return Notification.objects.create(user=self.user, kind=kind, title=title, summary=summary)

    def setUp(self):
        self.user = registered()

    def test_old_announcements_are_rewritten(self):
        shovll = self.make(
            Notification.KIND_WATCH_ON,
            f"shovll watch is on for {HOST}/v1",
            "shovll watch re-scans your API on a schedule and tells you when something gets worse.",
        )
        shovl = self.make(Notification.KIND_WATCH_ON, f"shovl watch is on for {HOST}/v1")
        self.rewrite()
        shovll.refresh_from_db()
        shovl.refresh_from_db()
        self.assertEqual(shovll.title, f"murindzi is on for {HOST}/v1")
        self.assertTrue(shovll.summary.startswith("murindzi re-scans your API"))
        self.assertEqual(shovl.title, f"murindzi is on for {HOST}/v1")

    def test_other_kinds_and_new_text_are_left_alone(self):
        alert = self.make(Notification.KIND_ALERT, "shovll watch found something", "kept as it was")
        current = self.make(Notification.KIND_WATCH_ON, f"murindzi is on for {HOST}/v1")
        self.rewrite()
        alert.refresh_from_db()
        current.refresh_from_db()
        self.assertEqual(alert.title, "shovll watch found something")
        self.assertEqual(current.title, f"murindzi is on for {HOST}/v1")

    def test_a_full_length_title_still_fits(self):
        long_title = "shovl watch is on for " + "a" * (200 - len("shovl watch is on for ") - 1) + "…"
        self.assertEqual(len(long_title), 200)
        item = self.make(Notification.KIND_WATCH_ON, long_title)
        self.rewrite()
        item.refresh_from_db()
        self.assertLessEqual(len(item.title), 200)
        self.assertTrue(item.title.startswith("murindzi is on for "))
        self.assertTrue(item.title.endswith("…"))

    def test_every_earlier_name_becomes_murindzi(self):
        items = [
            self.make(Notification.KIND_WATCH_ON, f"{name} is on for {HOST}/v1", f"{name} re-scans your API.")
            for name in ("shovl watch", "shovll watch", "xikomu watch")
        ]
        self.rewrite()
        for item in items:
            item.refresh_from_db()
            self.assertEqual(item.title, f"murindzi is on for {HOST}/v1")
            self.assertEqual(item.summary, "murindzi re-scans your API.")
