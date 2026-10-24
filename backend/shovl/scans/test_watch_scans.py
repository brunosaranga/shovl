"""
Scheduled scans (trigger "watch") stay out of the scan allowance (scans/limits.py): they
don't use up the 5 a day, don't count toward the attempt ceiling, and the stale-scan sweep
leaves them to the watch runner.

Run with:  DJANGO_DEBUG=1 python manage.py test scans
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from scans import limits
from scans.models import TRIGGER_MANUAL, TRIGGER_WATCH, Scan

User = get_user_model()

API = "https://api.example.com/v1"


def registered(email="real@example.com"):
    return User.objects.create_user(email, "correct horse battery staple", tos_agreed=True)


class ScheduledScansAndTheAllowanceTests(TestCase):
    def setUp(self):
        self.user = registered()

    def make(self, count, trigger, status="complete"):
        for _ in range(count):
            Scan.objects.create(user=self.user, target_url=API, status=status, trigger=trigger)

    def test_scans_are_manual_unless_told_otherwise(self):
        scan = Scan.objects.create(user=self.user, target_url=API)
        self.assertEqual(scan.trigger, TRIGGER_MANUAL)
        started = limits.start_scan(self.user, target_url=API)
        self.assertEqual(started.trigger, TRIGGER_MANUAL)

    def test_scheduled_scans_leave_the_daily_allowance_alone(self):
        self.make(limits.USER_SCANS_PER_DAY, TRIGGER_WATCH)
        allowance = limits.scans_remaining(self.user)
        self.assertEqual(allowance["used"], 0)
        self.assertEqual(allowance["remaining"], limits.USER_SCANS_PER_DAY)
        self.assertEqual(limits.start_scan(self.user, target_url=API).status, "running")

    def test_scheduled_attempts_leave_the_ceiling_alone(self):
        self.make(limits.USER_ATTEMPTS_PER_DAY, TRIGGER_WATCH, status="failed")
        self.assertEqual(limits.start_scan(self.user, target_url=API).status, "running")

    def test_manual_scans_still_count(self):
        self.make(limits.USER_SCANS_PER_DAY, TRIGGER_MANUAL)
        with self.assertRaises(limits.AllowanceExceeded) as refused:
            limits.start_scan(self.user, target_url=API)
        self.assertEqual(refused.exception.code, "daily_limit_reached")

    def test_a_running_scheduled_scan_is_neither_counted_nor_swept(self):
        scan = Scan.objects.create(user=self.user, target_url=API, status="running", trigger=TRIGGER_WATCH)
        long_ago = timezone.now() - limits.STALE_AFTER - timedelta(minutes=1)
        Scan.objects.filter(pk=scan.pk).update(created_at=long_ago)

        self.assertEqual(limits.scans_remaining(self.user)["used"], 0)
        limits.start_scan(self.user, target_url=API)

        scan.refresh_from_db()
        self.assertEqual(scan.status, "running")
