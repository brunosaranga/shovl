"""
GET and PATCH /api/accounts/me/: the plan and the two murindzi switches.

Run with:  DJANGO_DEBUG=1 python manage.py test accounts
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

User = get_user_model()

ME = "/api/accounts/me/"


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class MeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("real@example.com", "correct horse battery staple", tos_agreed=True)
        self.client = signed_in(self.user)

    def test_the_plan_and_the_switches(self):
        data = self.client.get(ME).data
        self.assertEqual(data["plan"], {"name": "free", "watch_slots": 1, "watch_cadence_days": 30})
        self.assertTrue(data["watch_enabled"])
        self.assertFalse(data["notifications_muted"])
        self.assertEqual(data["email"], "real@example.com")
        self.assertIn("allowance", data)

    @override_settings(SHOVL_WATCH_FREE_CADENCE_DAYS=7)
    def test_the_beta_cadence_shows(self):
        self.assertEqual(self.client.get(ME).data["plan"]["watch_cadence_days"], 7)

    def test_pro_and_staff(self):
        self.user.plan = User.PLAN_PRO
        self.user.save()
        self.assertEqual(self.client.get(ME).data["plan"]["name"], "pro")
        self.user.is_staff = True
        self.user.save()
        self.assertEqual(self.client.get(ME).data["plan"]["watch_slots"], None)

    def test_patch_the_switches(self):
        response = self.client.patch(ME, {"watch_enabled": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["watch_enabled"])
        response = self.client.patch(ME, {"notifications_muted": True, "watch_enabled": True}, format="json")
        self.assertTrue(response.data["notifications_muted"])
        self.assertTrue(response.data["watch_enabled"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.notifications_muted)

    def test_patch_cannot_change_anything_else(self):
        response = self.client.patch(
            ME,
            {"plan": "pro", "email": "someone-else@example.com", "is_staff": True, "token_version": 9},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.plan, User.PLAN_FREE)
        self.assertEqual(self.user.email, "real@example.com")
        self.assertFalse(self.user.is_staff)
        self.assertEqual(self.user.token_version, 0)
        self.assertEqual(response.data["plan"]["name"], "free")

    def test_patch_needs_booleans(self):
        response = self.client.patch(ME, {"watch_enabled": "no", "notifications_muted": 1}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {"watch_enabled", "notifications_muted"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.watch_enabled)

    def test_guests_can_read_but_not_change(self):
        guest = User.objects.create_guest(tos_agreed=True)
        client = signed_in(guest)
        self.assertEqual(client.get(ME).data["plan"]["watch_slots"], 0)
        response = client.patch(ME, {"watch_enabled": False}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "registration_required")
