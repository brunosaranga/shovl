"""
Tests for "since your last scan" (scans/compare.py) and what the report endpoint returns.

Run with:  python manage.py test scans
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from scanner.engine import build_raw
from scanner.report import format_report
from scans.compare import compare, comparison_for, previous_scan, target_key
from scans.models import Scan

User = get_user_model()

TARGET = "https://api.example.com/users"
CHECKS = [
    ("API5", "Security Misconfiguration"),
    ("API4", "Rate Limiting Absence"),
    ("API1", "Broken Object Level Authorization"),
    ("API2", "Broken Authentication"),
    ("API3", "Excessive Data Exposure"),
    ("API6", "Mass Assignment"),
]


def results(*severities, suggest_fix=False):
    """Saved results with one finding per check, severities in CHECKS order."""
    findings = [
        {"check": name, "id": check_id, "severity": severity, "detail": [f"{name} said {severity}"]}
        for (check_id, name), severity in zip(CHECKS, severities)
    ]
    return format_report(build_raw(TARGET, findings, suggest_fix=suggest_fix))


def registered_user(email="real@example.com"):
    return User.objects.create_user(email, "correct horse battery staple", tos_agreed=True)


def make_scan(user, url=TARGET, status="complete", severities=None, minutes_ago=0):
    report = results(*(severities or ["PASS"] * 6)) if status == "complete" else None
    scan = Scan.objects.create(
        user=user,
        target_url=url,
        status=status,
        results=report,
        risk_score=report["meta"]["risk_score"] if report else "",
        completed_at=timezone.now() if status == "complete" else None,
    )
    # created_at is set on save; move it back so the order is clear
    Scan.objects.filter(pk=scan.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
    scan.refresh_from_db()
    return scan


class TargetKeyTests(SimpleTestCase):
    def test_the_same_api_written_differently_is_the_same_target(self):
        same = [
            "https://api.example.com/users",
            "http://api.example.com/users",
            "https://API.Example.com/users/",
            "https://api.example.com:443/users",
            "http://api.example.com:80/users",
            "  https://api.example.com/users  ",
        ]
        keys = {target_key(url) for url in same}
        self.assertEqual(len(keys), 1)

    def test_a_different_path_query_or_port_is_another_target(self):
        base = target_key("https://api.example.com/users")
        for other in [
            "https://api.example.com/orders",
            "https://api.example.com/users?page=2",
            "https://api.example.com:8443/users",
            "https://other.example.com/users",
            "https://api.example.com/users/1",
        ]:
            self.assertNotEqual(target_key(other), base, other)

    def test_an_address_without_a_host_has_no_key(self):
        self.assertIsNone(target_key("not a url"))
        self.assertIsNone(target_key(""))
        self.assertIsNone(target_key(None))
        self.assertIsNone(target_key("https://api.example.com:99999/x"))


class CompareTests(SimpleTestCase):
    def changes(self, before, after):
        return {item["id"]: item["change"] for item in compare(results(*before), results(*after))["checks"]}

    def test_each_kind_of_change(self):
        changes = self.changes(
            ["HIGH", "PASS", "HIGH", "LOW", "MEDIUM", "PASS"],
            ["PASS", "MEDIUM", "MEDIUM", "HIGH", "MEDIUM", "PASS"],
        )
        self.assertEqual(changes, {
            "API5": "fixed",
            "API4": "new",
            "API1": "better",
            "API2": "worse",
            "API3": "same",
            "API6": "same",
        })

    def test_a_check_that_ran_on_one_side_only_cannot_be_compared(self):
        changes = self.changes(["ERROR", "HIGH"] + ["PASS"] * 4, ["LOW", "ERROR"] + ["PASS"] * 4)
        self.assertEqual(changes["API5"], "not_compared")
        self.assertEqual(changes["API4"], "not_compared")

    def test_a_check_that_could_not_run_in_either_scan_is_left_out(self):
        # mass assignment on a real domain is skipped every time
        result = compare(results(*["PASS"] * 5, "ERROR"), results(*["PASS"] * 5, "ERROR"))
        self.assertNotIn("API6", [item["id"] for item in result["checks"]])
        self.assertEqual(len(result["checks"]), 5)

    def test_counts_add_up(self):
        result = compare(results("HIGH", *["PASS"] * 5), results(*["PASS"] * 6))
        self.assertEqual(result["counts"]["fixed"], 1)
        self.assertEqual(result["counts"]["same"], 5)
        self.assertEqual(sum(result["counts"].values()), len(result["checks"]))

    def test_items_carry_before_after_and_the_check_name(self):
        item = compare(results("HIGH", *["PASS"] * 5), results(*["PASS"] * 6))["checks"][0]
        self.assertEqual(item, {
            "id": "API5", "check": "Security Misconfiguration", "before": "HIGH", "after": "PASS", "change": "fixed",
        })

    def test_odd_saved_results_do_not_break_it(self):
        self.assertEqual(compare(None, {})["checks"], [])
        self.assertEqual(compare({"findings": ["x", None]}, {"findings": [{"no": "id"}]})["checks"], [])
        weird = compare({"findings": [{"id": "API9", "severity": "odd"}]}, {"findings": [{"id": "API9", "severity": "HIGH"}]})
        self.assertEqual(weird["checks"][0]["change"], "not_compared")


class PreviousScanTests(TestCase):
    def setUp(self):
        self.user = registered_user()

    def test_the_newest_earlier_complete_scan_of_the_same_address(self):
        old = make_scan(self.user, minutes_ago=30)
        newer = make_scan(self.user, url="http://api.example.com/users/", minutes_ago=20)
        make_scan(self.user, status="failed", minutes_ago=10)
        make_scan(self.user, status="stopped", minutes_ago=9)
        current = make_scan(self.user, minutes_ago=0)
        self.assertEqual(previous_scan(current), newer)
        self.assertEqual(previous_scan(newer), old)
        self.assertIsNone(previous_scan(old))

    def test_later_scans_other_addresses_and_other_people_do_not_count(self):
        current = make_scan(self.user, minutes_ago=10)
        make_scan(self.user, minutes_ago=0)  # later
        make_scan(self.user, url="https://api.example.com/orders", minutes_ago=20)
        make_scan(registered_user("other@example.com"), minutes_ago=30)
        self.assertIsNone(previous_scan(current))

    def test_scans_started_at_the_same_moment_go_by_id(self):
        first = make_scan(self.user, minutes_ago=5)
        second = make_scan(self.user, minutes_ago=0)
        Scan.objects.filter(pk=second.pk).update(created_at=first.created_at)
        second.refresh_from_db()
        self.assertEqual(previous_scan(second), first)
        self.assertIsNone(previous_scan(first))

    def test_comparison_for_a_scan_with_nothing_before_it_is_none(self):
        self.assertIsNone(comparison_for(make_scan(self.user)))

    def test_comparison_for_a_scan_that_did_not_complete_is_none(self):
        make_scan(self.user, minutes_ago=10)
        self.assertIsNone(comparison_for(make_scan(self.user, status="running")))

    def test_comparison_names_the_earlier_scan_and_both_scores(self):
        old = make_scan(self.user, severities=["HIGH"] + ["PASS"] * 5, minutes_ago=10)
        current = make_scan(self.user, severities=["PASS"] * 6)
        comparison = comparison_for(current)
        self.assertEqual(comparison["previous"]["id"], old.pk)
        self.assertEqual(comparison["previous"]["target_url"], TARGET)
        self.assertTrue(comparison["previous"]["scanned_at"])
        self.assertEqual(comparison["risk"], {"before": "HIGH", "after": "LOW"})
        self.assertEqual(comparison["counts"]["fixed"], 1)


class ReportEndpointTests(TestCase):
    def setUp(self):
        self.user = registered_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_the_report_carries_the_comparison_and_feedback(self):
        make_scan(self.user, severities=["HIGH"] + ["PASS"] * 5, minutes_ago=10)
        current = make_scan(self.user)
        data = self.client.get(f"/api/scans/{current.pk}/").json()
        self.assertEqual(data["comparison"]["counts"]["fixed"], 1)
        self.assertIsNone(data["feedback"])

    def test_a_first_scan_has_no_comparison(self):
        data = self.client.get(f"/api/scans/{make_scan(self.user).pk}/").json()
        self.assertIsNone(data["comparison"])

    def test_the_list_leaves_both_out(self):
        make_scan(self.user, minutes_ago=10)
        make_scan(self.user)
        rows = self.client.get("/api/scans/").json()
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertNotIn("comparison", row)
            self.assertNotIn("feedback", row)

    def test_a_scan_still_running_is_served_without_a_comparison(self):
        make_scan(self.user, minutes_ago=10)
        running = make_scan(self.user, status="running")
        data = self.client.get(f"/api/scans/{running.pk}/").json()
        self.assertEqual(data["status"], "running")
        self.assertIsNone(data["comparison"])

    def test_someone_elses_scan_is_not_found(self):
        theirs = make_scan(registered_user("other@example.com"))
        self.assertEqual(self.client.get(f"/api/scans/{theirs.pk}/").status_code, 404)
