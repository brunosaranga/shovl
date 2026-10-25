"""
Tests for the PDF report (reporter/generator.py) and its download endpoint
(GET /api/scans/<id>/pdf/, ScanPDFView in scans/views.py).

Run with:  python manage.py test reporter
"""
import re
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from reporter import generator
from reporter.generator import build_pdf, esc, format_time, raw_lines
from scanner.engine import build_raw
from scanner.report import format_report
from scans.models import Scan
from scans.test_compare import make_scan, registered_user, results

TARGET = "https://api.example.com/users"


def pages(pdf):
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


def report_with(findings, **options):
    return format_report(build_raw(TARGET, findings, **options))


class BuildPdfTests(SimpleTestCase):
    def test_a_report_becomes_a_pdf(self):
        pdf = build_pdf(results("HIGH", "MEDIUM", "LOW", "PASS", "PASS", "ERROR"), scan_id=7)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertGreaterEqual(pages(pdf), 1)

    def test_the_sites_fonts_are_used(self):
        # Falling back to Helvetica would mean reporter/fonts/ went missing.
        self.assertEqual(generator.F["display"], "ShovllDisplay")
        self.assertEqual(generator.F["mono"], "ShovllMono")
        pdf = build_pdf(results(*["PASS"] * 6), scan_id=1)
        # Embedded subsets carry each font's own name.
        for face in (b"Arbutus", b"Inter", b"JetBrainsMono"):
            self.assertIn(face, pdf)
        for licence in ("OFL-Arbutus.txt", "OFL-Inter.txt", "OFL-JetBrainsMono.txt"):
            self.assertTrue((generator.FONT_DIR / licence).is_file(), licence)

    def test_text_from_the_scanned_api_is_never_read_as_markup(self):
        # Unescaped, ReportLab would try to open this image file and fail the whole PDF.
        hostile = '<img src="/no/such/file.png" width="10" height="10"/> & <b>bold</b> <font size=90>'
        report = report_with([
            {"check": hostile, "id": "API5", "severity": "HIGH", "detail": [hostile, "Server: " + hostile],
             "remediation": hostile},
        ], suggest_fix=True, verbose=True)
        report["meta"]["target"] = "https://x.test/<img src='/etc/passwd'/>"
        report["findings"][0]["raw"] = {"headers": {"Server": hostile}}
        pdf = build_pdf(report, scan_id=1, comparison={
            "previous": {"id": 1, "scanned_at": hostile}, "risk": {"before": hostile, "after": "HIGH"},
            "counts": {"new": 1}, "checks": [{"id": "API5", "check": hostile, "before": "PASS", "after": "HIGH", "change": "new"}],
        })
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_esc_turns_markup_into_text(self):
        self.assertEqual(esc('<img src="x"/> & co'), '&lt;img src="x"/&gt; &amp; co')
        self.assertEqual(esc("a\x00b\x1bc\td\ne"), "abc\td\ne")
        self.assertEqual(esc(None), "")

    def test_odd_and_foreign_text_still_builds(self):
        report = report_with([
            {"check": "Données exposées", "id": "API3", "severity": "MEDIUM",
             "detail": ["champ «mot_de_passe» — 密码 — пароль — 🔑", "\x00\x07 control"]},
            {"check": "Odd", "id": "API4", "severity": "PASS", "detail": "a single string, not a list"},
            {"check": "Empty", "id": "API1", "severity": "LOW", "detail": []},
        ])
        report["findings"].append("not a finding")
        self.assertTrue(build_pdf(report, scan_id=3).startswith(b"%PDF-"))

    def test_missing_pieces_do_not_break_it(self):
        for broken in ({}, None, {"meta": None, "findings": None, "summary": None}, {"meta": {"scanned_at": "yesterday"}}):
            self.assertTrue(build_pdf(broken, scan_id=1).startswith(b"%PDF-"), broken)

    def test_a_long_address_and_long_details_wrap_instead_of_running_off_the_page(self):
        long_url = "https://api.example.com/" + "segment/" * 60
        report = report_with([
            {"check": "BOLA", "id": "API1", "severity": "MEDIUM", "detail": [", ".join([long_url] * 5)]},
        ])
        report["meta"]["target"] = long_url
        self.assertTrue(build_pdf(report, scan_id=1).startswith(b"%PDF-"))

    def test_many_findings_flow_over_several_pages(self):
        findings = [
            {"check": f"Check {n}", "id": f"API{n}", "severity": "HIGH",
             "detail": ["a long explanation of what was found " * 6] * 3, "remediation": "fix it " * 30}
            for n in range(30)
        ]
        pdf = build_pdf(report_with(findings, suggest_fix=True), scan_id=1)
        self.assertGreater(pages(pdf), 3)

    def test_raw_responses_are_cut_short(self):
        lines, cut = raw_lines({"body": ["x" * 500] * 400})
        self.assertTrue(cut)
        self.assertEqual(len(lines), generator.RAW_MAX_LINES)
        self.assertTrue(all(len(line) <= generator.RAW_LINE_WIDTH for line in lines))

        short, cut = raw_lines({"status_code": 200})
        self.assertFalse(cut)
        self.assertEqual(short, ["{", '  "status_code": 200', "}"])

    def test_a_huge_verbose_scan_stays_a_small_file(self):
        findings = [
            {"check": f"Check {n}", "id": f"API{n}", "severity": "LOW", "detail": ["x"],
             "raw": {"response_preview": "y" * 1_000_000}}
            for n in range(6)
        ]
        pdf = build_pdf(report_with(findings, verbose=True), scan_id=1)
        self.assertLess(len(pdf), 400_000)

    def test_times_read_in_utc(self):
        self.assertEqual(format_time("2026-10-18T04:11:36+02:00"), "18 Oct 2026, 02:11 UTC")
        self.assertEqual(format_time("2026-10-18T02:11:36"), "18 Oct 2026, 02:11 UTC")
        self.assertEqual(format_time("not a time"), "not a time")
        self.assertEqual(format_time(None), "unknown")

    def test_generate_pdf_writes_a_file_for_local_scripts(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out" / "report.pdf"
            generator.generate_pdf(results(*["PASS"] * 6), path)
            self.assertTrue(path.read_bytes().startswith(b"%PDF-"))


class PdfDownloadTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = registered_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.scan = make_scan(self.user, severities=["HIGH"] + ["PASS"] * 5)

    def download(self, scan=None, client=None, **headers):
        return (client or self.client).get(f"/api/scans/{(scan or self.scan).pk}/pdf/", **headers)

    def test_a_finished_scan_downloads_as_a_pdf(self):
        response = self.download()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertRegex(
            response["Content-Disposition"],
            rf'^attachment; filename="shovll-report-api\.example\.com-\d{{4}}-\d{{2}}-\d{{2}}-{self.scan.pk}\.pdf"$',
        )
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertTrue(response.content.startswith(b"%PDF-"))

    def test_every_finished_scan_has_one_whatever_the_knobs(self):
        report = results(*["PASS"] * 6)
        report["meta"]["generate_report"] = False
        Scan.objects.filter(pk=self.scan.pk).update(results=report)
        self.assertEqual(self.download().status_code, 200)

    def test_nothing_is_written_to_disk(self):
        with patch.object(Path, "write_bytes") as write, patch("builtins.open") as opened:
            self.assertEqual(self.download().status_code, 200)
        write.assert_not_called()
        opened.assert_not_called()
        self.scan.refresh_from_db()
        self.assertEqual(self.scan.pdf_path, "")

    def test_downloads_are_counted(self):
        self.download()
        self.download()
        self.scan.refresh_from_db()
        self.assertEqual(self.scan.pdf_downloads, 2)
        make_scan(self.user, status="failed")
        self.download(Scan.objects.get(status="failed"))
        self.assertEqual(Scan.objects.get(status="failed").pdf_downloads, 0)

    def test_a_pdf_only_accept_header_is_fine(self):
        self.assertEqual(self.download(HTTP_ACCEPT="application/pdf").status_code, 200)

    def test_it_includes_since_your_last_scan(self):
        later = make_scan(self.user, severities=["PASS"] * 6)
        with patch("scans.views.build_pdf", wraps=build_pdf) as built:
            self.assertEqual(self.download(later).status_code, 200)
        comparison = built.call_args.kwargs["comparison"]
        self.assertEqual(comparison["previous"]["id"], self.scan.pk)
        self.assertEqual(comparison["counts"]["fixed"], 1)

    def test_someone_elses_scan_is_not_found(self):
        theirs = make_scan(registered_user("other@example.com"))
        response = self.download(theirs)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "not_found")
        self.assertEqual(self.client.get("/api/scans/999999/pdf/").status_code, 404)

    def test_sign_in_required(self):
        self.assertEqual(self.download(client=APIClient()).status_code, 401)

    def test_a_scan_that_did_not_finish_has_no_pdf(self):
        for status in ("running", "paused", "failed", "interrupted", "stopped"):
            scan = make_scan(self.user, status=status)
            response = self.download(scan)
            self.assertEqual(response.status_code, 409, status)
            self.assertEqual(response.json()["code"], "scan_not_complete")

    @override_settings(SHOVL_PDF_REPORTS=False)
    def test_the_switch_turns_downloads_off(self):
        with self.assertLogs("django.request", "ERROR"):
            response = self.download()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "pdf_disabled")

    def test_a_pdf_that_cannot_be_built_is_a_clear_error(self):
        with (
            patch("scans.views.build_pdf", side_effect=RuntimeError("boom")),
            self.assertLogs("scans.views", "ERROR"),
            self.assertLogs("django.request", "ERROR"),
        ):
            response = self.download()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "pdf_failed")

    def test_too_many_downloads_are_slowed_down(self):
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"pdf": "2/hour"}):
            codes = [self.download().status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_the_frontend_can_read_the_file_name(self):
        response = self.download(HTTP_ORIGIN="http://localhost:5173")
        self.assertIn("Content-Disposition", response["Access-Control-Expose-Headers"])

    def test_the_footer_names_the_site(self):
        with patch("scans.views.build_pdf", wraps=build_pdf) as built:
            self.download()
        self.assertEqual(built.call_args.kwargs["site"], "localhost:5173")
