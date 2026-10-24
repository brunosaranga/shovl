"""
The Watch model (watch/models.py): which API an address is, one watch per API per account,
what deleting things does, validation, pause and resume, and the admin.

Run with:  DJANGO_DEBUG=1 python manage.py test watch
"""
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from domains.models import Domain
from scans.compare import target_key
from scans.models import TRIGGER_WATCH, Scan
from scans.validators import MAX_URL_LENGTH
from watch.admin import WatchAdmin
from watch.models import Watch, watch_key

User = get_user_model()

PASSWORD = "correct horse battery staple"
API = "https://api.example.com/v1"


def registered(email="real@example.com", **fields):
    return User.objects.create_user(email, PASSWORD, tos_agreed=True, **fields)


def domain_for(user, hostname="api.example.com", verified=True):
    return Domain.objects.create(
        user=user,
        hostname=hostname,
        verified=verified,
        verified_at=timezone.now() if verified else None,
    )


def make_watch(user, domain, url=API, **fields):
    return Watch.objects.create(user=user, domain=domain, target_url=url, **fields)


class WatchKeyTests(SimpleTestCase):
    def test_one_api_written_several_ways(self):
        same = [
            API,
            "http://api.example.com/v1",
            "https://API.example.com/v1/",
            "https://api.example.com:443/v1",
            "http://api.example.com:80/v1",
        ]
        self.assertEqual(len({watch_key(url) for url in same}), 1)

    def test_different_apis(self):
        different = [
            API,
            "https://api.example.com/v2",
            "https://api.example.com/v1?page=2",
            "https://api.example.com:8443/v1",
            "https://other.example.com/v1",
        ]
        self.assertEqual(len({watch_key(url) for url in different}), len(different))

    def test_same_rule_as_since_your_last_scan(self):
        addresses = [
            API,
            "http://API.example.com/v1/",
            "https://api.example.com/v1?x=1",
            "https://api.example.com:8080/v1",
            "https://api.example.com",
            "https://api.example.com/",
        ]
        for a in addresses:
            for b in addresses:
                with self.subTest(a=a, b=b):
                    self.assertEqual(watch_key(a) == watch_key(b), target_key(a) == target_key(b))

    def test_always_64_characters(self):
        long_url = "https://api.example.com/" + "é" * (MAX_URL_LENGTH - 24)
        for url in (API, long_url):
            key = watch_key(url)
            self.assertEqual(len(key), 64)
            int(key, 16)

    def test_no_host_no_key(self):
        for url in ("", None, "not a url", "https://", "https://[::1"):
            with self.subTest(url=url):
                self.assertIsNone(watch_key(url))


class WatchModelTests(TestCase):
    def setUp(self):
        self.user = registered()
        self.domain = domain_for(self.user)

    def test_saving_sets_the_key(self):
        watch = make_watch(self.user, self.domain)
        watch.refresh_from_db()
        self.assertEqual(watch.target_key, watch_key(API))

    def test_changing_the_address_updates_the_key(self):
        watch = make_watch(self.user, self.domain)
        watch.target_url = "https://api.example.com/v2"
        watch.save(update_fields=["target_url"])
        watch.refresh_from_db()
        self.assertEqual(watch.target_key, watch_key("https://api.example.com/v2"))

    def test_one_watch_per_api_per_account(self):
        make_watch(self.user, self.domain, API)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_watch(self.user, self.domain, "http://API.example.com/v1/")

    def test_another_account_can_watch_the_same_api(self):
        other = registered("other@example.com")
        make_watch(self.user, self.domain)
        make_watch(other, domain_for(other))
        self.assertEqual(Watch.objects.count(), 2)

    def test_a_long_address_fits(self):
        prefix = "https://api.example.com/"
        for filler in ("a", "é"):
            url = prefix + filler * (MAX_URL_LENGTH - len(prefix))
            with self.subTest(filler=filler):
                self.assertEqual(len(url), MAX_URL_LENGTH)
                watch = make_watch(self.user, self.domain, url)
                watch.refresh_from_db()
                self.assertEqual(watch.target_url, url)
                watch.delete()

    def test_a_new_watch(self):
        before = timezone.now()
        watch = make_watch(self.user, self.domain)
        self.assertTrue(watch.active)
        self.assertFalse(watch.is_paused)
        self.assertEqual(watch.consecutive_failures, 0)
        self.assertLessEqual(before, watch.next_run_at)
        self.assertLessEqual(watch.next_run_at, timezone.now())
        self.assertIsNone(watch.last_run_at)
        self.assertIsNone(watch.last_scan)

    def test_slots_go_in_activation_order(self):
        now = timezone.now()
        later = make_watch(self.user, self.domain, API, activated_at=now - timedelta(days=1))
        earlier = make_watch(self.user, self.domain, "https://api.example.com/v2", activated_at=now - timedelta(days=3))
        self.assertEqual(list(Watch.objects.filter(user=self.user)), [earlier, later])

    def test_deleting_the_domain_deletes_its_watches(self):
        make_watch(self.user, self.domain)
        self.domain.delete()
        self.assertFalse(Watch.objects.exists())

    def test_deleting_the_account_deletes_its_watches(self):
        make_watch(self.user, self.domain)
        self.user.delete()
        self.assertFalse(Watch.objects.exists())

    def test_deleting_the_last_scan_keeps_the_watch(self):
        scan = Scan.objects.create(user=self.user, target_url=API, status="complete", trigger=TRIGGER_WATCH)
        watch = make_watch(self.user, self.domain, last_scan=scan)
        scan.delete()
        watch.refresh_from_db()
        self.assertIsNone(watch.last_scan)

    def test_an_address_without_a_host_is_refused(self):
        with self.assertRaises(ValueError):
            Watch(user=self.user, domain=self.domain, target_url="nonsense").save()
        self.assertFalse(Watch.objects.exists())


class WatchValidationTests(TestCase):
    def setUp(self):
        self.user = registered()
        self.domain = domain_for(self.user)

    def assert_invalid(self, watch, field):
        with self.assertRaises(ValidationError) as refused:
            watch.full_clean()
        self.assertIn(field, refused.exception.message_dict)

    def test_a_valid_watch(self):
        Watch(user=self.user, domain=self.domain, target_url=API).full_clean()

    def test_the_address_must_be_on_the_domain(self):
        self.assert_invalid(Watch(user=self.user, domain=self.domain, target_url="https://other.example.com/v1"), "target_url")

    def test_a_subdomain_is_a_different_domain(self):
        # Verification is per host name (as on the scan endpoints), so v2.api.example.com isn't covered.
        self.assert_invalid(Watch(user=self.user, domain=self.domain, target_url="https://v2.api.example.com/"), "target_url")

    def test_someone_elses_domain(self):
        other = registered("other@example.com")
        self.assert_invalid(Watch(user=self.user, domain=domain_for(other), target_url=API), "domain")

    def test_an_unverified_domain_cannot_get_a_new_watch(self):
        pending = domain_for(self.user, "pending.example.com", verified=False)
        self.assert_invalid(Watch(user=self.user, domain=pending, target_url="https://pending.example.com/v1"), "domain")

    def test_an_existing_watch_stays_editable_if_its_domain_loses_verification(self):
        watch = make_watch(self.user, self.domain)
        self.domain.verified = False
        self.domain.save()
        watch.refresh_from_db()
        watch.full_clean()

    def test_a_second_watch_of_the_same_api_is_an_error_not_a_crash(self):
        make_watch(self.user, self.domain, API)
        self.assert_invalid(Watch(user=self.user, domain=self.domain, target_url="http://API.example.com/v1/"), "target_url")

    def test_an_address_without_a_host(self):
        self.assert_invalid(Watch(user=self.user, domain=self.domain, target_url="https://"), "target_url")


class PauseAndResumeTests(TestCase):
    def setUp(self):
        user = registered()
        self.watch = make_watch(user, domain_for(user))

    def test_pause_records_why_and_when(self):
        when = timezone.now()
        self.watch.pause(Watch.PAUSED_VERIFICATION, now=when)
        self.watch.refresh_from_db()
        self.assertTrue(self.watch.is_paused)
        self.assertEqual(self.watch.paused_reason, Watch.PAUSED_VERIFICATION)
        self.assertEqual(self.watch.paused_at, when)

    def test_pause_refuses_an_unknown_reason(self):
        with self.assertRaises(ValueError):
            self.watch.pause("bored")
        self.watch.refresh_from_db()
        self.assertFalse(self.watch.is_paused)

    def test_resume_starts_again_with_a_clean_slate(self):
        self.watch.consecutive_failures = Watch.MAX_FAILURES
        self.watch.next_run_at = timezone.now() + timedelta(days=7)
        self.watch.save()
        self.watch.pause(Watch.PAUSED_FAILURES)

        when = timezone.now()
        self.watch.resume(now=when)
        self.watch.refresh_from_db()
        self.assertFalse(self.watch.is_paused)
        self.assertIsNone(self.watch.paused_at)
        self.assertEqual(self.watch.consecutive_failures, 0)
        self.assertEqual(self.watch.next_run_at, when)


class WatchAdminTests(TestCase):
    def setUp(self):
        self.boss = User.objects.create_superuser("boss@example.com", PASSWORD)
        self.client.force_login(self.boss)
        self.user = registered()
        self.domain = domain_for(self.user)
        self.watch = make_watch(self.user, self.domain, next_run_at=timezone.now() + timedelta(days=7))

    def test_the_list_and_the_watch_open(self):
        response = self.client.get(reverse("admin:watch_watch_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, API)
        response = self.client.get(reverse("admin:watch_watch_change", args=[self.watch.pk]))
        self.assertEqual(response.status_code, 200)

    def test_due_now(self):
        self.client.post(reverse("admin:watch_watch_changelist"), {
            "action": "make_due_now",
            "_selected_action": [self.watch.pk],
        })
        self.watch.refresh_from_db()
        self.assertLessEqual(self.watch.next_run_at, timezone.now())

    def test_resume(self):
        self.watch.consecutive_failures = Watch.MAX_FAILURES
        self.watch.save()
        self.watch.pause(Watch.PAUSED_FAILURES)
        self.client.post(reverse("admin:watch_watch_changelist"), {
            "action": "resume_selected",
            "_selected_action": [self.watch.pk],
        })
        self.watch.refresh_from_db()
        self.assertFalse(self.watch.is_paused)
        self.assertEqual(self.watch.consecutive_failures, 0)

    def test_the_state_column(self):
        state = WatchAdmin(Watch, admin.site).state
        self.assertEqual(state(self.watch), "on")

        self.user.watch_enabled = False
        self.user.save()
        self.watch.refresh_from_db()
        self.assertEqual(state(self.watch), "on (account switch off)")

        self.watch.active = False
        self.assertEqual(state(self.watch), "off")

        self.watch.pause(Watch.PAUSED_FAILURES)
        self.assertEqual(state(self.watch), f"paused: failed {Watch.MAX_FAILURES} runs in a row")

    def test_adding_a_duplicate_shows_an_error(self):
        response = self.client.post(reverse("admin:watch_watch_add"), {
            "user": self.user.pk,
            "domain": self.domain.pk,
            "target_url": "http://API.example.com/v1/",
            "active": "on",
            "activated_at_0": "2026-10-21",
            "activated_at_1": "12:00:00",
            "next_run_at_0": "2026-10-21",
            "next_run_at_1": "12:00:00",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already watches this API")
        self.assertEqual(Watch.objects.count(), 1)
