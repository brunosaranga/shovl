"""
One address is one account, however it is typed: stored lowercased, found in any
case at sign-in, and backed by a case-insensitive unique rule in the database.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import GUEST_EMAIL_DOMAIN

User = get_user_model()

PASSWORD = "plum-cactus-harbour-42"

REGISTER_URL = "/api/accounts/register/"
LOGIN_URL = "/api/accounts/login/"
UPGRADE_URL = "/api/accounts/upgrade/"


class EmailCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def register(self, email):
        return self.client.post(
            REGISTER_URL,
            {"email": email, "password": PASSWORD, "tos_agreed": True},
            format="json",
        )

    def login(self, email, password=PASSWORD):
        return self.client.post(
            LOGIN_URL,
            {"email": email, "password": password},
            format="json",
        )

    def upgrade(self, guest, email):
        # A separate client, so the main one stays signed out for the other calls.
        client = APIClient()
        client.force_authenticate(user=guest)
        return client.post(
            UPGRADE_URL,
            {"email": email, "password": PASSWORD, "tos_agreed": True},
            format="json",
        )

    def make_guest(self):
        return User.objects.create_guest(tos_agreed=True)

    # ---- stored lowercased -------------------------------------------------------

    def test_register_stores_the_whole_address_lowercased(self):
        response = self.register("  Bruno.Test@Example.COM ")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(User.objects.filter(email="bruno.test@example.com").exists())
        self.assertEqual(User.objects.count(), 1)

    def test_upgrade_stores_the_whole_address_lowercased(self):
        guest = self.make_guest()
        response = self.upgrade(guest, "New.Person@Example.com")
        self.assertEqual(response.status_code, 200, response.data)
        guest.refresh_from_db()
        self.assertEqual(guest.email, "new.person@example.com")
        self.assertFalse(guest.is_guest)

    def test_manager_and_plain_save_lowercase_too(self):
        staff = User.objects.create_superuser("Staff.Member@Example.com", PASSWORD)
        self.assertEqual(staff.email, "staff.member@example.com")

        # The admin's add form saves through save(), not the manager.
        made_in_admin = User(email="Admin.Made@Example.com")
        made_in_admin.set_unusable_password()
        made_in_admin.save()
        made_in_admin.refresh_from_db()
        self.assertEqual(made_in_admin.email, "admin.made@example.com")

    def test_manager_refuses_a_blank_address(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("   ", PASSWORD)

    # ---- one account per address ------------------------------------------------

    def test_register_refuses_the_same_address_in_another_case(self):
        self.assertEqual(self.register("bruno@example.com").status_code, 201)
        response = self.register("Bruno@Example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_upgrade_refuses_an_address_taken_in_another_case(self):
        self.assertEqual(self.register("taken@example.com").status_code, 201)
        guest = self.make_guest()
        response = self.upgrade(guest, "TAKEN@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        guest.refresh_from_db()
        self.assertTrue(guest.is_guest)

    def test_database_refuses_case_only_duplicates(self):
        User.objects.create_user("a.person@example.com", PASSWORD)
        other = User.objects.create_user("other@example.com", PASSWORD)
        # update() skips save(), so only the database rule stands in the way.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.filter(pk=other.pk).update(email="A.Person@Example.com")

    def test_full_clean_reports_a_case_only_duplicate(self):
        User.objects.create_user("a.person@example.com", PASSWORD)
        candidate = User(email="A.Person@Example.com", password="unused")
        with self.assertRaises(ValidationError):
            candidate.full_clean()

    def test_guests_are_not_affected(self):
        first, second = self.make_guest(), self.make_guest()
        for guest in (first, second):
            self.assertTrue(guest.email.endswith("@" + GUEST_EMAIL_DOMAIN))
            self.assertEqual(guest.email, guest.email.lower())
        self.assertNotEqual(first.email, second.email)

    # ---- sign-in ----------------------------------------------------------------

    def test_sign_in_works_in_any_case(self):
        self.assertEqual(self.register("bruno@example.com").status_code, 201)
        for typed in ("bruno@example.com", "Bruno@Example.com", "BRUNO@EXAMPLE.COM"):
            response = self.login(typed)
            self.assertEqual(response.status_code, 200, (typed, response.data))
            self.assertIn("access", response.data)

    def test_sign_in_still_refuses_a_wrong_password(self):
        self.assertEqual(self.register("bruno@example.com").status_code, 201)
        response = self.login("Bruno@Example.com", password="not-the-password-99")
        self.assertEqual(response.status_code, 401)
