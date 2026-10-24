"""
The watch endpoints (watch/views.py), the watch badge and trigger on the scan endpoints, and a
watch starting by itself when a scan of a verified domain completes on either scan endpoint.

The scan-flow tests never touch the network: reachability and the checks are replaced.

Run with:  DJANGO_DEBUG=1 python manage.py test watch
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from domains.models import Domain
from scanner.engine import CHECK_INFO, CHECKS
from scans import views as scan_views
from scans.models import TRIGGER_WATCH, Scan
from watch import services
from watch.models import Watch

User = get_user_model()

PASSWORD = "correct horse battery staple"
HOST = "api.example.com"
API = f"https://{HOST}/v1"
API2 = f"https://{HOST}/v2"
PRACTICE = "https://postman-echo.com/get"
LIST = "/api/watches/"


def registered(email="real@example.com", **fields):
    return User.objects.create_user(email, PASSWORD, tos_agreed=True, **fields)


def domain_for(user, hostname=HOST, verified=True):
    return Domain.objects.create(user=user, hostname=hostname, verified=verified, verified_at=timezone.now() if verified else None)


def scan_of(user, url=API, status="complete", trigger="manual"):
    return Scan.objects.create(user=user, target_url=url, status=status, trigger=trigger, completed_at=timezone.now())


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class WatchEndpointTests(TestCase):
    def setUp(self):
        self.user = registered()
        domain_for(self.user)
        self.client = signed_in(self.user)

    def test_list(self):
        first = services.watch_after_scan(scan_of(self.user, API))
        response = self.client.get(LIST)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["id"], first.pk)
        self.assertEqual(item["target_url"], API)
        self.assertTrue(item["active"])
        self.assertTrue(item["in_plan"])
        self.assertEqual(item["paused_reason"], "")

    def test_the_list_is_yours_only(self):
        other = registered("other@example.com")
        domain_for(other)
        services.watch_after_scan(scan_of(other, API))
        self.assertEqual(self.client.get(LIST).data, [])

    def test_watch_this_api(self):
        scan = scan_of(self.user)
        response = self.client.post(LIST, {"scan": scan.pk}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["watch"]["target_url"], API)
        self.assertEqual(response.data["state"]["status"], "watching")

        again = self.client.post(LIST, {"scan": scan.pk}, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(Watch.objects.count(), 1)

    def test_a_full_plan_then_instead(self):
        services.watch_after_scan(scan_of(self.user, API))
        scan = scan_of(self.user, API2)

        response = self.client.post(LIST, {"scan": scan.pk}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "plan_full")
        self.assertTrue(response.data["can_swap"])
        self.assertEqual(response.data["watch_slots"], 1)

        response = self.client.post(LIST, {"scan": scan.pk, "instead": True}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["state"]["status"], "watching")
        self.assertEqual(Watch.objects.filter(active=True).get().target_url, API2)

    def test_bad_bodies(self):
        scan = scan_of(self.user)
        for body in ({}, {"scan": "1"}, {"scan": True}, {"scan": None}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post(LIST, body, format="json").status_code, 400)
        response = self.client.post(LIST, {"scan": scan.pk, "instead": "yes"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Watch.objects.exists())

    def test_someone_elses_scan_is_not_found(self):
        other = registered("other@example.com")
        domain_for(other)
        response = self.client.post(LIST, {"scan": scan_of(other).pk}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "not_found")

    def test_refused_for_a_practice_target_and_an_unverified_domain(self):
        response = self.client.post(LIST, {"scan": scan_of(self.user, PRACTICE).pk}, format="json")
        self.assertEqual((response.status_code, response.data["code"]), (400, "practice_target"))
        domain_for(self.user, "pending.example.com", verified=False)
        response = self.client.post(LIST, {"scan": scan_of(self.user, "https://pending.example.com/").pk}, format="json")
        self.assertEqual((response.status_code, response.data["code"]), (403, "domain_not_verified"))

    def test_turn_off_and_on(self):
        watch = services.watch_after_scan(scan_of(self.user))
        url = f"{LIST}{watch.pk}/"
        response = self.client.patch(url, {"active": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["active"])
        self.assertFalse(response.data["in_plan"])
        response = self.client.patch(url, {"active": True}, format="json")
        self.assertTrue(response.data["active"])
        self.assertTrue(response.data["in_plan"])

    def test_turn_on_without_room(self):
        watch = services.watch_after_scan(scan_of(self.user, API))
        services.set_active(self.user, watch, False)
        services.watch_after_scan(scan_of(self.user, API2))
        response = self.client.patch(f"{LIST}{watch.pk}/", {"active": True}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "plan_full")

    def test_patch_needs_a_boolean(self):
        watch = services.watch_after_scan(scan_of(self.user))
        for body in ({}, {"active": "false"}, {"active": 0}):
            with self.subTest(body=body):
                self.assertEqual(self.client.patch(f"{LIST}{watch.pk}/", body, format="json").status_code, 400)

    def test_resume(self):
        watch = services.watch_after_scan(scan_of(self.user))
        watch.pause(Watch.PAUSED_FAILURES)
        response = self.client.post(f"{LIST}{watch.pk}/resume/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["paused_reason"], "")

    def test_someone_elses_watch_is_not_found(self):
        other = registered("other@example.com")
        domain_for(other)
        theirs = services.watch_after_scan(scan_of(other))
        self.assertEqual(self.client.patch(f"{LIST}{theirs.pk}/", {"active": False}, format="json").status_code, 404)
        self.assertEqual(self.client.post(f"{LIST}{theirs.pk}/resume/").status_code, 404)
        theirs.refresh_from_db()
        self.assertTrue(theirs.active)

    def test_guests_and_strangers(self):
        guest = User.objects.create_guest(tos_agreed=True)
        response = signed_in(guest).get(LIST)
        self.assertEqual((response.status_code, response.data["code"]), (403, "registration_required"))
        self.assertEqual(APIClient().get(LIST).status_code, 401)


class ScanEndpointFieldTests(TestCase):
    def setUp(self):
        self.user = registered()
        domain_for(self.user)
        self.client = signed_in(self.user)

    def test_the_report_carries_the_badge(self):
        scan = scan_of(self.user)
        services.watch_after_scan(scan)
        data = self.client.get(f"/api/scans/{scan.pk}/").data
        self.assertEqual(data["watch"]["status"], "watching")
        self.assertEqual(data["trigger"], "manual")

    def test_a_practice_report_has_no_badge(self):
        scan = scan_of(self.user, PRACTICE)
        self.assertIsNone(self.client.get(f"/api/scans/{scan.pk}/").data["watch"])

    def test_the_list_says_what_started_each_scan(self):
        scan_of(self.user)
        scan_of(self.user, trigger=TRIGGER_WATCH)
        items = self.client.get("/api/scans/").data
        self.assertEqual(sorted(item["trigger"] for item in items), ["manual", "watch"])
        self.assertNotIn("watch", items[0])


def at_once(func, *args, **kwargs):
    """Stands in for while_working: runs the check in this thread, with no keep-alives."""
    return func(*args, **kwargs)
    yield  # never reached; makes this a generator, like the real one


def passing_check(module_path, target_url, token=None, verbose=False, budget=None, allow_writes=False):
    name, check_id = CHECK_INFO[module_path]
    return {"check": name, "id": check_id, "severity": "PASS", "detail": ["fine"]}


def passing_scan(target_url, **kwargs):
    findings = [passing_check(path, target_url) for path in CHECKS]
    return scan_views.build_raw(target_url, findings)


class ScanStartsAWatchTests(TestCase):
    """A completed scan of a verified domain starts the watch, on both scan endpoints."""

    def setUp(self):
        self.user = registered()
        domain_for(self.user)
        self.client = signed_in(self.user)
        for target, value in [
            ("preflight", lambda *args, **kwargs: None),
            ("while_working", at_once),
            ("run_check", passing_check),
            ("run_scan", passing_scan),
        ]:
            patcher = patch.object(scan_views, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def stream(self, url=API):
        response = self.client.get("/api/scans/stream/", {"target_url": url})
        self.assertEqual(response.status_code, 200)
        return b"".join(response.streaming_content).decode()

    def test_the_stream(self):
        body = self.stream()
        self.assertIn('"status": "complete"', body)
        watch = Watch.objects.get()
        self.assertEqual(watch.target_url, API)
        self.assertEqual(Scan.objects.get().status, "complete")

    def test_the_blocking_endpoint(self):
        response = self.client.post("/api/scans/create/", {"target_url": API}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Watch.objects.filter(user=self.user, target_url=API).exists())

    def test_a_practice_scan_starts_nothing(self):
        self.stream(PRACTICE)
        self.assertFalse(Watch.objects.exists())

    def test_a_problem_starting_the_watch_never_fails_the_scan(self):
        with patch.object(scan_views, "watch_after_scan", side_effect=RuntimeError("bug")), \
                self.assertLogs("scans.views", level="ERROR"):
            body = self.stream()
        self.assertIn('"status": "complete"', body)
        self.assertEqual(Scan.objects.get().status, "complete")
        self.assertFalse(Watch.objects.exists())
