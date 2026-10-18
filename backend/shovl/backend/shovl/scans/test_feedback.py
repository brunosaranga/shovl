"""
Tests for the optional "was this report useful?" answer (POST /api/scans/<id>/feedback/).

Run with:  python manage.py test scans
"""
import io
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from scans.models import Scan, ScanFeedback
from scans.test_compare import make_scan, registered_user

User = get_user_model()


def url(scan):
    return f"/api/scans/{scan.pk}/feedback/"


class FeedbackTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = registered_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.scan = make_scan(self.user, severities=["HIGH", "MEDIUM", "PASS", "PASS", "LOW", "PASS"])

    def post(self, body, scan=None, client=None):
        return (client or self.client).post(url(scan or self.scan), body, format="json")

    def test_the_first_answer_must_say_whether_it_was_useful(self):
        response = self.post({"comment": "nice"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("useful", response.json())
        self.assertFalse(ScanFeedback.objects.exists())

    def test_an_answer_is_saved_with_a_copy_of_the_report(self):
        response = self.post({"useful": True})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"useful": True, "comment": "", "would_pay": ""})

        answer = ScanFeedback.objects.get()
        self.assertEqual(answer.scan, self.scan)
        self.assertEqual(answer.risk_score, "HIGH")
        self.assertEqual(answer.summary, {"HIGH": 1, "MEDIUM": 1, "LOW": 1, "PASS": 3, "ERROR": 0})
        self.assertEqual((answer.checks_run, answer.total_checks), (6, 6))
        self.assertFalse(answer.practice_target)
        self.assertFalse(answer.guest)
        self.assertEqual(answer.options, {"generate_report": True, "suggest_fix": False, "verbose": False})

    def test_later_answers_add_to_the_same_row(self):
        self.post({"useful": False})
        response = self.post({"comment": "  more detail on BOLA please  ", "would_pay": "maybe"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"useful": False, "comment": "more detail on BOLA please", "would_pay": "maybe"}
        )
        self.assertEqual(self.post({"useful": True}).json()["useful"], True)
        self.assertEqual(ScanFeedback.objects.count(), 1)

    def test_the_report_shows_the_answer(self):
        self.post({"useful": True, "would_pay": "yes"})
        data = self.client.get(f"/api/scans/{self.scan.pk}/").json()
        self.assertEqual(data["feedback"], {"useful": True, "comment": "", "would_pay": "yes"})

    def test_bad_answers_are_refused(self):
        self.assertEqual(self.post({}).status_code, 400)
        self.assertEqual(self.post({"useful": True, "would_pay": "lots"}).status_code, 400)
        self.assertEqual(self.post({"useful": True, "comment": "x" * 501}).status_code, 400)
        self.assertEqual(self.post({"useful": True, "comment": "nul\x00"}).status_code, 400)
        self.assertEqual(self.post({"useful": "perhaps"}).status_code, 400)
        self.assertEqual(self.post({"useful": True, "comment": ["a"]}).status_code, 400)
        self.assertFalse(ScanFeedback.objects.exists())

    def test_a_comment_keeps_its_lines_but_not_control_characters(self):
        response = self.post({"useful": True, "comment": "line one\r\nline\x1b two\x07"})
        self.assertEqual(response.json()["comment"], "line one\nline two")

    def test_a_500_character_comment_fits(self):
        self.assertEqual(self.post({"useful": True, "comment": "x" * 500}).status_code, 201)

    def test_only_your_own_finished_scans(self):
        theirs = make_scan(registered_user("other@example.com"))
        self.assertEqual(self.post({"useful": True}, scan=theirs).status_code, 404)
        running = make_scan(self.user, status="running")
        response = self.post({"useful": True}, scan=running)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "scan_not_complete")
        self.assertEqual(APIClient().post(url(self.scan), {"useful": True}, format="json").status_code, 401)

    def test_post_only(self):
        self.assertEqual(self.client.get(url(self.scan)).status_code, 405)

    def test_guests_can_answer(self):
        guest = User.objects.create_guest(tos_agreed=True)
        client = APIClient()
        client.force_authenticate(guest)
        scan = make_scan(guest, url="https://postman-echo.com/get")
        response = self.post({"useful": False}, scan=scan, client=client)
        self.assertEqual(response.status_code, 201)
        answer = ScanFeedback.objects.get(scan=scan)
        self.assertTrue(answer.guest)
        self.assertTrue(answer.practice_target)

    def test_the_answer_outlives_the_scan_without_pointing_to_anyone(self):
        self.post({"useful": True, "comment": "good"})
        self.scan.delete()
        answer = ScanFeedback.objects.get()
        self.assertIsNone(answer.scan)
        self.assertEqual(answer.comment, "good")
        self.assertEqual(answer.risk_score, "HIGH")

    def test_the_answer_outlives_the_guest_clean_up(self):
        guest = User.objects.create_guest(tos_agreed=True)
        client = APIClient()
        client.force_authenticate(guest)
        scan = make_scan(guest, url="https://postman-echo.com/get")
        self.post({"useful": True}, scan=scan, client=client)
        User.objects.filter(pk=guest.pk).update(date_joined=timezone.now() - timedelta(days=40))

        call_command("purge_guests", stdout=io.StringIO())

        self.assertFalse(User.objects.filter(pk=guest.pk).exists())
        answer = ScanFeedback.objects.get()
        self.assertIsNone(answer.scan)
        self.assertTrue(answer.guest)

    def test_too_many_answers_are_slowed_down(self):
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"feedback": "3/hour"}):
            codes = [self.post({"useful": True}).status_code for _ in range(4)]
        self.assertEqual(codes, [201, 200, 200, 429])
