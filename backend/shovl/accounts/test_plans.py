"""
Plans (accounts/plans.py), the account fields shovll watch adds, and the accounts admin.

Run with:  DJANGO_DEBUG=1 python manage.py test accounts
"""
import os
import subprocess
import sys
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts import plans

User = get_user_model()

PASSWORD = "correct horse battery staple"


def registered(email="real@example.com", **fields):
    return User.objects.create_user(email, PASSWORD, tos_agreed=True, **fields)


class NewAccountTests(TestCase):
    def test_new_account_is_free_with_watch_on_and_not_muted(self):
        user = registered()
        user.refresh_from_db()
        self.assertEqual(user.plan, User.PLAN_FREE)
        self.assertTrue(user.watch_enabled)
        self.assertFalse(user.notifications_muted)
        self.assertIsNone(user.watch_intro_at)

    def test_guest_gets_the_same_defaults(self):
        guest = User.objects.create_guest(tos_agreed=True)
        guest.refresh_from_db()
        self.assertEqual(guest.plan, User.PLAN_FREE)
        self.assertTrue(guest.watch_enabled)


class EffectivePlanTests(TestCase):
    def test_free(self):
        plan = plans.effective_plan(registered())
        self.assertEqual(plan.name, "free")
        self.assertEqual(plan.watch_slots, plans.FREE_WATCH_SLOTS)
        self.assertEqual(plan.watch_cadence, timedelta(days=30))
        self.assertTrue(plan.can_watch)

    def test_pro(self):
        plan = plans.effective_plan(registered(plan=User.PLAN_PRO))
        self.assertEqual(plan.name, "pro")
        self.assertEqual(plan.watch_slots, plans.PRO_WATCH_SLOTS)
        self.assertEqual(plan.watch_cadence, timedelta(days=7))

    def test_staff_has_no_limit_and_scans_weekly(self):
        plan = plans.effective_plan(registered(is_staff=True))
        self.assertEqual(plan.name, "staff")
        self.assertIsNone(plan.watch_slots)
        self.assertTrue(plan.can_watch)
        self.assertEqual(plan.watch_cadence, timedelta(days=7))

    def test_guest_cannot_watch_whatever_the_plan_says(self):
        guest = User.objects.create_guest(tos_agreed=True, plan=User.PLAN_PRO)
        plan = plans.effective_plan(guest)
        self.assertEqual(plan.name, "guest")
        self.assertEqual(plan.watch_slots, 0)
        self.assertFalse(plan.can_watch)

    @override_settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7)
    def test_beta_cadence_changes_free(self):
        self.assertEqual(plans.effective_plan(registered()).watch_cadence, timedelta(days=7))

    @override_settings(SHOVL_WATCH_FREE_CADENCE_DAYS=14)
    def test_free_cadence_leaves_pro_alone(self):
        pro = registered(plan=User.PLAN_PRO)
        self.assertEqual(plans.effective_plan(pro).watch_cadence, timedelta(days=7))

    def test_a_failed_payment_falls_back_to_free_without_changing_the_account(self):
        user = registered(plan=User.PLAN_PRO)
        with patch.object(plans, "pro_is_paid", return_value=False):
            plan = plans.effective_plan(user)
        self.assertEqual(plan.name, "free")
        self.assertEqual(plan.watch_slots, plans.FREE_WATCH_SLOTS)
        user.refresh_from_db()
        self.assertEqual(user.plan, User.PLAN_PRO)

    def test_a_failed_payment_does_not_affect_staff(self):
        user = registered(plan=User.PLAN_PRO, is_staff=True)
        with patch.object(plans, "pro_is_paid", return_value=False):
            self.assertEqual(plans.effective_plan(user).name, "staff")

    def test_the_plan_is_worked_out_on_every_call(self):
        user = registered()
        self.assertEqual(plans.effective_plan(user).name, "free")
        user.plan = User.PLAN_PRO
        self.assertEqual(plans.effective_plan(user).name, "pro")


class FreeCadenceSettingTests(TestCase):
    """WATCH_FREE_CADENCE_DAYS is read when the app starts; a bad value stops it starting."""

    def start_app(self, value):
        env = {**os.environ, "DJANGO_DEBUG": "1", "WATCH_FREE_CADENCE_DAYS": value}
        code = "import django; django.setup(); from django.conf import settings; print(settings.SHOVL_WATCH_FREE_CADENCE_DAYS)"
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=settings.BASE_DIR,
            env={**env, "DJANGO_SETTINGS_MODULE": "core.settings"},
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_a_number_of_days(self):
        result = self.start_app("7")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "7")

    def test_zero_is_refused(self):
        result = self.start_app("0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("WATCH_FREE_CADENCE_DAYS must be at least 1", result.stderr)

    def test_not_a_number_is_refused(self):
        result = self.start_app("weekly")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("WATCH_FREE_CADENCE_DAYS must be a whole number", result.stderr)


class UserAdminTests(TestCase):
    def setUp(self):
        self.boss = User.objects.create_superuser("boss@example.com", PASSWORD)
        self.client.force_login(self.boss)

    def test_the_list_shows_the_plan_and_what_it_gets(self):
        registered("pro@example.com", plan=User.PLAN_PRO)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pro@example.com")
        self.assertContains(response, "Pro")

    def test_the_plan_can_be_changed_but_not_the_email(self):
        user = registered()
        url = reverse("admin:accounts_user_change", args=[user.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, {
            "plan": User.PLAN_PRO,
            "watch_enabled": "on",
            "is_active": "on",
            "email": "someone-else@example.com",
            "is_staff": "on",
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.plan, User.PLAN_PRO)
        self.assertEqual(user.email, "real@example.com")
        self.assertFalse(user.is_staff)
        self.assertEqual(plans.effective_plan(user).name, "pro")

    def test_accounts_are_not_created_here(self):
        response = self.client.get(reverse("admin:accounts_user_add"))
        self.assertEqual(response.status_code, 403)
