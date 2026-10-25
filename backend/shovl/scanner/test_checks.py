"""
Tests for how the authentication, BOLA and misconfiguration checks judge what they see.

Run with:  python manage.py test scanner

No network is used: the checks' requests are answered by small scripted fakes.
"""
import json
from unittest import mock

import requests
from django.test import SimpleTestCase

from scanner import engine, evidence, http
from scanner.checks import auth, bola, mass_assignment, misconfig, rate_limit

BASE = "https://api.example.com/items"


def reply(status=200, body=None, kind="application/json", text=None, truncated=False):
    response = requests.Response()
    response.status_code = status
    response.headers["Content-Type"] = kind
    response._content = (text if text is not None else json.dumps(body)).encode()
    response.encoding = "utf-8"
    response.truncated = truncated
    return response


def page():
    return reply(200, kind="text/html", text="<!doctype html><html><body>Sign in</body></html>")


def serve(rules):
    """Answer every request the checks make with rules(url, headers)."""
    return mock.patch(
        "scanner.http.get",
        side_effect=lambda url, headers=None, **kw: rules(url, headers or {}),
    )


def run_auth(no_token, bad_token, valid=None, token=None, verbose=False):
    def rules(url, headers):
        sent = headers.get("Authorization")
        if sent is None:
            return no_token()
        if sent == f"Bearer {auth.BAD_TOKEN}":
            return bad_token()
        return valid()

    with serve(rules):
        return auth.run(BASE, token=token, verbose=verbose)


DATA = {"products": [{"id": 1}]}


class AuthPublicEndpointTests(SimpleTestCase):
    def test_a_public_endpoint_that_ignores_the_header_is_medium_not_high(self):
        result = run_auth(lambda: reply(200, DATA), lambda: reply(200, DATA))
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertEqual(len(result["detail"]), 1)
        self.assertIn("Open to anyone", result["detail"][0])

    def test_optional_authentication_is_medium_and_says_tokens_are_checked(self):
        result = run_auth(lambda: reply(200, DATA), lambda: reply(401, {"error": "bad token"}))
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertTrue(any("Invalid tokens are refused" in d for d in result["detail"]))

    def test_a_login_page_is_low_and_not_an_open_api(self):
        result = run_auth(page, page)
        self.assertEqual(result["severity"], "LOW")
        self.assertIn("web page", result["detail"][0])


class AuthRealProblemTests(SimpleTestCase):
    def test_an_invalid_token_that_gets_through_is_high(self):
        result = run_auth(lambda: reply(401, {"error": "no token"}), lambda: reply(200, DATA))
        self.assertEqual(result["severity"], "HIGH")
        self.assertIn("invalid token", result["detail"][0])

    def test_the_same_answer_with_your_token_and_without_is_high(self):
        result = run_auth(
            lambda: reply(200, DATA), lambda: reply(200, DATA),
            valid=lambda: reply(200, DATA), token="real",
        )
        self.assertEqual(result["severity"], "HIGH")
        self.assertIn("not enforced", result["detail"][0])

    def test_less_data_without_the_token_is_medium(self):
        result = run_auth(
            lambda: reply(200, {"products": []}), lambda: reply(200, {"products": []}),
            valid=lambda: reply(200, DATA), token="real",
        )
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertTrue(any("different content" in d for d in result["detail"]))

    def test_a_token_that_does_not_work_is_said_so(self):
        result = run_auth(
            lambda: reply(200, DATA), lambda: reply(200, DATA),
            valid=lambda: reply(401, {}), token="expired",
        )
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertTrue(any("could not be compared" in d for d in result["detail"]))


class AuthPassTests(SimpleTestCase):
    def test_everything_refused_passes(self):
        result = run_auth(lambda: reply(401, {}), lambda: reply(401, {}))
        self.assertEqual(result["severity"], "PASS")
        self.assertEqual(result["detail"], ["Authentication controls appear to be in place"])

    def test_refused_without_a_token_when_a_token_is_supplied_passes(self):
        result = run_auth(
            lambda: reply(403, {}), lambda: reply(403, {}),
            valid=lambda: reply(200, DATA), token="real",
        )
        self.assertEqual(result["severity"], "PASS")


class AuthNothingToAssessTests(SimpleTestCase):
    def test_a_404_is_low_and_never_pass(self):
        result = run_auth(lambda: reply(404, {"error": "no"}), lambda: reply(404, {"error": "no"}))
        self.assertEqual(result["severity"], "LOW")
        self.assertIn("Nothing was found at this URL (404)", result["detail"][0])
        self.assertIn("could not be assessed", result["detail"][0])

    def test_a_410_says_nothing_was_found(self):
        result = run_auth(lambda: reply(410, {}), lambda: reply(410, {}))
        self.assertEqual(result["severity"], "LOW")
        self.assertIn("Nothing was found", result["detail"][0])

    def test_other_non_answers_are_low_and_name_the_status(self):
        for status in (400, 405, 429, 500, 503):
            result = run_auth(lambda s=status: reply(s, {}), lambda s=status: reply(s, {}))
            self.assertEqual(result["severity"], "LOW", status)
            self.assertIn(f"answered {status} without a token", result["detail"][0])

    def test_a_refusal_is_still_a_pass(self):
        for status in (401, 403):
            result = run_auth(lambda s=status: reply(s, {}), lambda s=status: reply(s, {}))
            self.assertEqual(result["severity"], "PASS", status)

    def test_a_404_with_a_token_supplied_is_still_low(self):
        result = run_auth(
            lambda: reply(404, {}), lambda: reply(404, {}),
            valid=lambda: reply(200, DATA), token="real",
        )
        self.assertEqual(result["severity"], "LOW")


class AuthOtherTests(SimpleTestCase):
    def test_the_supplied_token_is_sent_and_the_bad_one_is_not_the_supplied_one(self):
        seen = []

        def rules(url, headers):
            seen.append(headers.get("Authorization"))
            return reply(401, {})

        with serve(rules):
            auth.run(BASE, token="real")
        self.assertEqual(seen, [None, f"Bearer {auth.BAD_TOKEN}", "Bearer real"])

    def test_verbose_reports_the_statuses(self):
        result = run_auth(lambda: reply(401, {}), lambda: reply(401, {}), verbose=True)
        self.assertEqual(result["raw"], {"no_auth_status": 401, "bad_auth_status": 401})

    def test_an_unreachable_target_is_an_error(self):
        with mock.patch("scanner.http.get", side_effect=http.ScanRequestError("timeout")):
            result = auth.run(BASE)
        self.assertEqual((result["severity"], result["reason"]), ("ERROR", "timeout"))


def run_bola(objects=None, token=None, catch_all=None, status_for_missing=404, verbose=False):
    """
    `objects` maps an ID to the JSON body returned for it. `catch_all` is a
    function(url) giving a response for every URL, for servers that answer
    everything the same way.
    """
    calls = []

    def rules(url, headers):
        calls.append((url, headers.get("Authorization")))
        if catch_all:
            return catch_all(url)
        object_id = int(url.rsplit("/", 1)[1])
        if objects and object_id in objects:
            return reply(200, objects[object_id])
        return reply(status_for_missing, {"error": "no"})

    with serve(rules):
        result = bola.run(BASE, token=token, verbose=verbose)
    return result, calls


class BolaTests(SimpleTestCase):
    def test_distinct_objects_without_login_are_medium(self):
        result, _ = run_bola({1: {"id": 1}, 2: {"id": 2}, 3: {"id": 3}})
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertIn(f"{BASE}/1", result["detail"][0])
        self.assertIn("public", result["detail"][0])

    def test_a_single_readable_object_is_still_flagged(self):
        result, _ = run_bola({1: {"id": 1}})
        self.assertEqual(result["severity"], "MEDIUM")

    def test_never_high(self):
        result, _ = run_bola({n: {"id": n} for n in bola.PROBE_IDS})
        self.assertNotEqual(result["severity"], "HIGH")

    def test_a_catch_all_json_server_passes(self):
        result, _ = run_bola(catch_all=lambda url: reply(200, {"ok": True}))
        self.assertEqual(result["severity"], "PASS")
        self.assertIn("No evidence", result["detail"][0])

    def test_an_echo_server_passes(self):
        result, _ = run_bola(catch_all=lambda url: reply(200, {"url": url}))
        self.assertEqual(result["severity"], "PASS")

    def test_a_single_page_app_passes(self):
        result, _ = run_bola(catch_all=lambda url: page())
        self.assertEqual(result["severity"], "PASS")

    def test_identical_bodies_for_different_ids_pass(self):
        same = {"message": "hello"}
        result, _ = run_bola({1: same, 2: same, 3: same})
        self.assertEqual(result["severity"], "PASS")

    def test_ids_that_require_login_pass_and_no_baseline_is_sent(self):
        result, calls = run_bola(status_for_missing=401)
        self.assertEqual(result["severity"], "PASS")
        self.assertEqual(len(calls), len(bola.PROBE_IDS))

    def test_a_cut_short_body_is_not_treated_as_an_object(self):
        result, _ = run_bola(catch_all=lambda url: reply(200, {"a": 1}, truncated=True))
        self.assertEqual(result["severity"], "PASS")


class BolaWithTokenTests(SimpleTestCase):
    def test_objects_returned_with_a_token_are_low_and_say_how_to_confirm(self):
        result, _ = run_bola({1: {"id": 1, "owner": "me"}, 2: {"id": 2, "owner": "you"}}, token="real")
        self.assertEqual(result["severity"], "LOW")
        self.assertIn("second account", result["detail"][0])

    def test_nothing_returned_with_a_token_passes(self):
        result, _ = run_bola(status_for_missing=403, token="real")
        self.assertEqual(result["severity"], "PASS")

    def test_the_token_is_sent_on_every_probe(self):
        _, calls = run_bola({1: {"id": 1}}, token="real")
        self.assertTrue(all(sent == "Bearer real" for _, sent in calls))

    def test_verbose_lists_the_probes_and_marks_the_baseline(self):
        result, _ = run_bola({1: {"id": 1}}, verbose=True)
        self.assertEqual(len(result["raw"]), len(bola.PROBE_IDS) + 1)
        self.assertTrue(result["raw"][-1]["baseline"])

    def test_an_unreachable_target_is_an_error(self):
        with mock.patch("scanner.http.get", side_effect=http.ScanRequestError("dns")):
            result = bola.run(BASE)
        self.assertEqual((result["severity"], result["reason"]), ("ERROR", "dns"))


class EvidenceTests(SimpleTestCase):
    def test_html_is_recognised_by_header_or_by_content(self):
        self.assertTrue(evidence.is_html(page()))
        self.assertTrue(evidence.is_html(reply(200, kind="text/plain", text="  <!DOCTYPE html><p>")))
        self.assertFalse(evidence.is_html(reply(200, {"a": 1})))

    def test_json_body_needs_a_non_empty_object_or_list(self):
        self.assertEqual(evidence.json_body(reply(200, {"a": 1})), {"a": 1})
        self.assertIsNone(evidence.json_body(reply(200, {})))
        self.assertIsNone(evidence.json_body(reply(200, 5)))
        self.assertIsNone(evidence.json_body(page()))

    def test_same_body_compares_content_and_never_trusts_a_cut_short_body(self):
        self.assertTrue(evidence.same_body(reply(200, {"a": 1}), reply(200, {"a": 1})))
        self.assertFalse(evidence.same_body(reply(200, {"a": 1}), reply(200, {"a": 2})))
        self.assertFalse(
            evidence.same_body(reply(200, {"a": 1}, truncated=True), reply(200, {"a": 1}))
        )
        self.assertTrue(
            evidence.same_body(
                reply(200, kind="text/plain", text="hi "), reply(200, kind="text/plain", text="hi")
            )
        )


def run_mass_assignment(respond, token=None, verbose=False):
    """`respond(sent_json)` gives the response for what the check POSTed."""
    sent = []

    def fake_post(url, json=None, headers=None, **kwargs):
        sent.append((json, headers))
        return respond(json)

    with mock.patch("scanner.http.post", side_effect=fake_post):
        result = mass_assignment.run(BASE, token=token, verbose=verbose)
    return result, sent


class MassAssignmentTests(SimpleTestCase):
    def test_an_echo_server_is_low_and_not_high(self):
        result, _ = run_mass_assignment(lambda sent: reply(200, {"args": {}, "json": sent}))
        self.assertEqual(result["severity"], "LOW")
        self.assertIn("returns whatever it is sent", result["detail"][0])

    def test_an_echo_that_returns_the_body_as_a_string_is_low(self):
        result, _ = run_mass_assignment(lambda sent: reply(200, {"data": json.dumps(sent)}))
        self.assertEqual(result["severity"], "LOW")

    def test_privileged_fields_accepted_and_control_dropped_is_high(self):
        result, _ = run_mass_assignment(
            lambda sent: reply(201, {"id": 7, "is_admin": True, "role": "admin"})
        )
        self.assertEqual(result["severity"], "HIGH")
        self.assertIn("is_admin", result["detail"][0])
        self.assertIn("role", result["detail"][0])

    def test_a_nested_field_is_found(self):
        result, _ = run_mass_assignment(lambda sent: reply(201, {"user": {"is_admin": True}}))
        self.assertEqual(result["severity"], "HIGH")

    def test_the_same_value_as_text_or_number_is_found(self):
        result, _ = run_mass_assignment(lambda sent: reply(200, {"balance": "99999"}))
        self.assertEqual(result["severity"], "HIGH")

    def test_a_response_that_ignored_the_fields_is_medium_not_high(self):
        result, _ = run_mass_assignment(
            lambda sent: reply(201, {"id": 1, "role": "user", "email_verified": False, "is_admin": False})
        )
        self.assertEqual(result["severity"], "MEDIUM")

    def test_a_rejection_that_names_the_field_is_not_high(self):
        result, _ = run_mass_assignment(
            lambda sent: reply(400, {"errors": {"is_admin": ["not allowed"], "role": ["not allowed"]}})
        )
        self.assertEqual(result["severity"], "PASS")

    def test_an_echo_style_error_is_not_high(self):
        result, _ = run_mass_assignment(lambda sent: reply(422, {"received": sent}))
        self.assertEqual(result["severity"], "PASS")

    def test_a_url_that_does_not_take_posts_passes(self):
        result, _ = run_mass_assignment(lambda sent: reply(405, {"error": "method not allowed"}))
        self.assertEqual(result["severity"], "PASS")

    def test_a_response_that_is_not_json_is_skipped(self):
        result, _ = run_mass_assignment(lambda sent: reply(200, kind="text/plain", text="ok"))
        self.assertEqual(result["severity"], "PASS")
        self.assertIn("not JSON", result["detail"][0])

    def test_the_request_carries_the_injected_and_the_control_fields(self):
        _, sent = run_mass_assignment(lambda body: reply(200, {}), token="real")
        body, headers = sent[0]
        for field, value in mass_assignment.INJECTED_FIELDS.items():
            self.assertEqual(body[field], value)
        self.assertEqual(body[mass_assignment.CONTROL_FIELD], mass_assignment.CONTROL_VALUE)
        self.assertEqual(headers["Authorization"], "Bearer real")

    def test_verbose_reports_what_was_found(self):
        result, _ = run_mass_assignment(
            lambda sent: reply(201, {"is_admin": True}), verbose=True
        )
        self.assertEqual(result["raw"]["accepted"], ["is_admin"])
        self.assertFalse(result["raw"]["control_returned"])

    def test_an_unreachable_target_is_an_error(self):
        with mock.patch("scanner.http.post", side_effect=http.ScanRequestError("tls")):
            result = mass_assignment.run(BASE)
        self.assertEqual((result["severity"], result["reason"]), ("ERROR", "tls"))


MASS_ASSIGNMENT = "scanner.checks.mass_assignment"


class WriteChecksAreSkippedByDefaultTests(SimpleTestCase):
    def test_mass_assignment_is_the_write_check(self):
        self.assertEqual(engine.WRITE_CHECKS, {MASS_ASSIGNMENT})
        self.assertIn(MASS_ASSIGNMENT, engine.CHECKS)

    def test_it_is_skipped_by_default_and_nothing_is_sent(self):
        with mock.patch("scanner.http.post") as post:
            finding = engine.run_check(MASS_ASSIGNMENT, BASE)
        post.assert_not_called()
        self.assertEqual(finding["severity"], "ERROR")
        self.assertEqual(finding["reason"], "not_run")
        self.assertEqual(finding["id"], "API6")
        self.assertIn("opt-in", finding["detail"][0])

    def test_it_is_skipped_when_writes_are_explicitly_off(self):
        with mock.patch("scanner.http.post") as post:
            finding = engine.run_check(MASS_ASSIGNMENT, BASE, allow_writes=False)
        post.assert_not_called()
        self.assertEqual(finding["reason"], "not_run")

    def test_it_runs_when_writes_are_allowed(self):
        with mock.patch("scanner.http.post", return_value=reply(200, {"json": {}})) as post:
            finding = engine.run_check(MASS_ASSIGNMENT, BASE, allow_writes=True)
        post.assert_called_once()
        self.assertNotEqual(finding["severity"], "ERROR")

    def test_read_only_checks_are_not_affected(self):
        with mock.patch("scanner.http.get", return_value=reply(401, {})):
            finding = engine.run_check("scanner.checks.auth", BASE)
        self.assertNotEqual(finding.get("reason"), "not_run")

    def test_skipping_does_not_depend_on_the_time_budget(self):
        expired = mock.Mock(expired=True)
        finding = engine.run_check(MASS_ASSIGNMENT, BASE, budget=expired)
        self.assertEqual(finding["reason"], "not_run")

    def test_run_scan_passes_the_flag_to_every_check(self):
        for flag in (False, True):
            with mock.patch("scanner.engine.preflight"), \
                 mock.patch("scanner.engine.run_check", return_value={"severity": "PASS"}) as run_check:
                engine.run_scan(BASE, allow_writes=flag)
            self.assertEqual(run_check.call_count, len(engine.CHECKS))
            self.assertTrue(
                all(call.kwargs["allow_writes"] is flag for call in run_check.call_args_list)
            )

    def test_run_scan_skips_writes_unless_told_otherwise(self):
        with mock.patch("scanner.engine.preflight"), \
             mock.patch("scanner.engine.run_check", return_value={"severity": "PASS"}) as run_check:
            engine.run_scan(BASE)
        self.assertTrue(all(call.kwargs["allow_writes"] is False for call in run_check.call_args_list))

    def test_a_skipped_check_makes_the_report_partial_but_the_scan_usable(self):
        findings = [
            {"check": "A", "id": "API1", "severity": "PASS", "detail": ["ok"]},
            engine._error_finding(MASS_ASSIGNMENT, engine.NOT_RUN_MESSAGE, "not_run"),
        ]
        engine.ensure_usable(findings)    # must not raise: one check really ran
        # Only the check that ran counts; the skipped one is not a clean result.
        self.assertEqual(engine._calculate_risk(findings), "LOW")
        self.assertEqual(
            engine._calculate_risk([findings[1]]), "INCOMPLETE"
        )


def run_rate_limit(statuses, headers=None, verbose=False):
    """Answer each request with the next status in `statuses`, then keep repeating the last one."""
    sent = []

    def fake_get(url, headers_=None, **kwargs):
        index = min(len(sent), len(statuses) - 1)
        sent.append(statuses[index])
        response = reply(statuses[index], {"ok": True})
        response.headers.update(headers or {})
        return response

    with mock.patch("scanner.http.get", side_effect=lambda url, **kw: fake_get(url, **kw)), \
         mock.patch("scanner.checks.rate_limit.time.sleep"):
        result = rate_limit.run(BASE, verbose=verbose)
    return result, sent


class RateLimitTests(SimpleTestCase):
    def test_a_429_is_a_pass_and_stops_the_burst(self):
        result, sent = run_rate_limit([200, 200, 200, 429])
        self.assertEqual(result["severity"], "PASS")
        self.assertIn("429 received after 4 requests", result["detail"][0])
        self.assertEqual(len(sent), 4)

    def test_nothing_at_all_is_medium_not_high(self):
        result, sent = run_rate_limit([200])
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertEqual(len(sent), rate_limit.BURST_COUNT)
        self.assertIn("no 429 and no rate-limit headers", result["detail"][0])
        self.assertIn("may be higher", result["detail"][0])

    def test_never_high(self):
        for statuses in ([200], [401], [404], [500]):
            result, _ = run_rate_limit(statuses)
            self.assertNotEqual(result["severity"], "HIGH")

    def test_an_advertised_limit_passes_even_without_a_429(self):
        result, _ = run_rate_limit([200], headers={"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "99"})
        self.assertEqual(result["severity"], "PASS")
        self.assertIn("X-RateLimit-Limit: 100", result["detail"][0])

    def test_the_standard_and_alternative_header_names_are_recognised(self):
        for name in ("RateLimit-Limit", "RateLimit-Policy", "x-rate-limit-limit", "X-RateLimit-Limit-Minute"):
            result, _ = run_rate_limit([200], headers={name: "60"})
            self.assertEqual(result["severity"], "PASS", name)

    def test_unrelated_headers_do_not_count(self):
        result, _ = run_rate_limit([200], headers={"X-Request-Id": "abc", "Retry-After": "5"})
        self.assertEqual(result["severity"], "MEDIUM")

    def test_a_header_seen_only_on_a_later_response_still_counts(self):
        seen = []

        def fake_get(url, **kwargs):
            seen.append(1)
            response = reply(200, {})
            if len(seen) == 7:
                response.headers["RateLimit-Remaining"] = "3"
            return response

        with mock.patch("scanner.http.get", side_effect=fake_get), \
             mock.patch("scanner.checks.rate_limit.time.sleep"):
            result = rate_limit.run(BASE)
        self.assertEqual(result["severity"], "PASS")

    def test_the_token_is_sent_on_every_request(self):
        seen = []

        def fake_get(url, headers=None, **kwargs):
            seen.append((headers or {}).get("Authorization"))
            return reply(200, {})

        with mock.patch("scanner.http.get", side_effect=fake_get), \
             mock.patch("scanner.checks.rate_limit.time.sleep"):
            rate_limit.run(BASE, token="real")
        self.assertEqual(seen, ["Bearer real"] * rate_limit.BURST_COUNT)

    def test_verbose_reports_statuses_and_headers(self):
        result, _ = run_rate_limit([200, 429], headers={"RateLimit-Limit": "2"}, verbose=True)
        self.assertEqual(result["raw"]["status_codes"], [200, 429])
        self.assertEqual(result["raw"]["rate_limit_headers"], {"RateLimit-Limit": "2"})

    def test_an_unreachable_target_is_an_error(self):
        with mock.patch("scanner.http.get", side_effect=http.ScanRequestError("timeout")):
            result = rate_limit.run(BASE)
        self.assertEqual((result["severity"], result["reason"]), ("ERROR", "timeout"))

def headers_reply(**headers):
    response = reply(404, kind="text/html", text="<h1>Not Found</h1>")
    for name, value in headers.items():
        response.headers[name.replace("_", "-")] = value
    return response


def run_misconfig(response, url="https://api.example.com"):
    with serve(lambda url, headers: response):
        return misconfig.run(url, verbose=True)


class MisconfigTests(SimpleTestCase):
    def test_a_server_name_without_a_version_is_not_a_finding(self):
        # What a CDN or host sets in front of almost every API (shovll's own scan, 25 Oct 2026)
        for server in ("cloudflare", "nginx", "Apache", "AmazonS3", "Google Frontend"):
            with self.subTest(server=server):
                result = run_misconfig(headers_reply(Server=server))
                self.assertEqual(result["severity"], "PASS")
                self.assertEqual(result["detail"], ["No misconfigurations detected"])

    def test_a_server_version_is_low_and_quoted(self):
        for server in ("nginx/1.18.0", "Apache/2.4.41 (Ubuntu)", "Microsoft-IIS/10.0", "Jetty(9.4.43.v20210629)"):
            with self.subTest(server=server):
                result = run_misconfig(headers_reply(Server=server))
                self.assertEqual(result["severity"], "LOW")
                self.assertEqual(result["detail"], [f"Server header reveals the software version: {server}"])

    def test_framework_headers_are_low(self):
        result = run_misconfig(headers_reply(X_Powered_By="Express", X_AspNet_Version="4.0.30319"))
        self.assertEqual(result["severity"], "LOW")
        self.assertIn("X-Powered-By header reveals the framework: Express", result["detail"])
        self.assertIn("X-AspNet-Version header reveals the framework: 4.0.30319", result["detail"])

    def test_header_names_are_matched_whatever_their_case(self):
        result = run_misconfig(headers_reply(**{"x_powered_by": "PHP/8.1.2"}))
        self.assertEqual(result["severity"], "LOW")

    def test_a_cors_wildcard_is_still_medium_and_outranks_low(self):
        result = run_misconfig(headers_reply(Server="nginx/1.18.0", Access_Control_Allow_Origin="*"))
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertEqual(len(result["detail"]), 2)

    def test_plain_http_is_still_high(self):
        result = run_misconfig(headers_reply(Server="cloudflare"), url="http://api.example.com")
        self.assertEqual(result["severity"], "HIGH")
        self.assertEqual(result["detail"], ["API not served over HTTPS"])

    def test_verbose_keeps_the_headers(self):
        result = run_misconfig(headers_reply(Server="cloudflare"))
        self.assertEqual(result["raw"]["status_code"], 404)
        self.assertEqual(result["raw"]["headers"]["Server"], "cloudflare")
