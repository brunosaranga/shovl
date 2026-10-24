"""
Scans finishing at the same moment can't all take the plan's last slot: the account row is
locked while a watch starts (watch/services.py). The lock only takes effect on Postgres, so
this test is skipped on SQLite.

Run against Postgres:  DATABASE_URL=postgresql://... DJANGO_DEBUG=1 python manage.py test watch
"""
import threading
import time
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from domains.models import Domain
from scans.models import Scan
from watch import services
from watch.models import Watch

User = get_user_model()


@skipUnless(connection.vendor == "postgresql", "the row lock only takes effect on Postgres")
class LastSlotRaceTests(TransactionTestCase):
    ATTEMPTS = 6

    def test_simultaneous_scans_take_one_free_slot(self):
        user = User.objects.create_user("racer@example.com", "correct horse battery staple", tos_agreed=True)
        Domain.objects.create(user=user, hostname="api.example.com", verified=True, verified_at=timezone.now())
        scans = [
            Scan.objects.create(user=user, target_url=f"https://api.example.com/v{n}", status="complete", completed_at=timezone.now())
            for n in range(self.ATTEMPTS)
        ]

        original = services.has_room
        barrier = threading.Barrier(self.ATTEMPTS)

        def slow_has_room(*args, **kwargs):
            # Widens the gap between "is there room?" and creating the watch.
            answer = original(*args, **kwargs)
            time.sleep(0.3)
            return answer

        def finish(scan):
            try:
                barrier.wait()
                services.watch_after_scan(Scan.objects.select_related("user").get(pk=scan.pk))
            finally:
                connection.close()

        with patch.object(services, "has_room", slow_has_room):
            threads = [threading.Thread(target=finish, args=(scan,)) for scan in scans]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(Watch.objects.filter(user=user).count(), 1)
