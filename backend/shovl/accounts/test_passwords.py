"""
Tests for password strength when an account is registered or upgraded.

Run with:  python manage.py test accounts
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()

REGISTER = "/api/accounts/register/"
UPGRADE = "/api/accounts/upgrade/"
LOGIN = "/api/accounts/login/"

STRONG = "correct horse battery staple"


def register_body(password, email="new@example.com"):
    return {"email": email, "password": password, "tos_agreed": True}


class RegisterPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def post(self, password, email="new@example.com"):
        return self.client.post(REGISTER, register_body(password, email), format="json")

    def test_a_strong_password_registers(self):
        response = self.post(STRONG)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_a_password_shorter_than_ten_characters_is_refused(self):
        response = self.post("Sh0rt!pw9")
        self.assertEqual(response.status_code, 400)
        self.assertIn("too short", " ".join(response.data["password"]))
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_ten_characters_is_enough_when_nothing_else_is_wrong(self):
        self.assertEqual(self.post("v7!Kq2#mXp").status_code, 201)

    def test_a_common_password_is_refused(self):
        response = self.post("qwertyuiop")
        self.assertEqual(response.status_code, 400)
        self.assertIn("too common", " ".join(response.data["password"]))

    def test_an_all_numeric_password_is_refused(self):
        response = self.post("48271950362918")
        self.assertEqual(response.status_code, 400)
        self.assertIn("entirely numeric", " ".join(response.data["password"]))

    def test_a_password_too_similar_to_the_email_is_refused(self):
        response = self.post("alexandria12", email="alexandria@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("too similar", " ".join(response.data["password"]))

    def test_every_problem_is_reported_at_once(self):
        response = self.post("12345")
        self.assertEqual(response.status_code, 400)
        self.assertGreaterEqual(len(response.data["password"]), 2)

    def test_an_overlong_password_is_refused(self):
        response = self.post("aB3$" * 33)
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_the_password_error_never_echoes_the_password(self):
        response = self.post("qwertyuiop")
        self.assertNotIn("qwertyuiop", str(response.data))


class UpgradePasswordTests(TestCase):
    def setUp(self):
        self.guest = User.objects.create_guest(tos_agreed=True)
        self.client = APIClient()
        self.client.force_authenticate(self.guest)

    def upgrade(self, password, email="real@example.com"):
        return self.client.post(UPGRADE, register_body(password, email), format="json")

    def test_a_strong_password_upgrades_the_guest(self):
        response = self.upgrade(STRONG)
        self.assertEqual(response.status_code, 200)
        self.guest.refresh_from_db()
        self.assertFalse(self.guest.is_guest)
        self.assertEqual(self.guest.email, "real@example.com")
        self.assertTrue(self.guest.check_password(STRONG))

    def test_a_weak_password_is_refused_and_the_guest_stays_a_guest(self):
        placeholder = self.guest.email
        response = self.upgrade("qwertyuiop")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)
        self.guest.refresh_from_db()
        self.assertTrue(self.guest.is_guest)
        self.assertEqual(self.guest.email, placeholder)
        self.assertFalse(self.guest.has_usable_password())

    def test_a_short_password_is_refused(self):
        self.assertEqual(self.upgrade("Sh0rt!pw9").status_code, 400)

    def test_similarity_is_checked_against_the_new_email(self):
        response = self.upgrade("alexandria12", email="alexandria@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("too similar", " ".join(response.data["password"]))


class LoginIsNotAffectedTests(TestCase):
    def test_an_existing_weak_password_can_still_sign_in(self):
        User.objects.create_user("old@example.com", "weak", tos_agreed=True)
        response = APIClient().post(
            LOGIN, {"email": "old@example.com", "password": "weak"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_a_new_strong_password_signs_in_after_registering(self):
        client = APIClient()
        client.post(REGISTER, register_body(STRONG), format="json")
        response = client.post(
            LOGIN, {"email": "new@example.com", "password": STRONG}, format="json"
        )
        self.assertEqual(response.status_code, 200)