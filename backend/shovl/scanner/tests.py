"""
Tests for the scanner's safety layer (scanner/http.py).

Run with:  python manage.py test scanner

Most tests use fake responses and a fake DNS, so they need no network. A few
start tiny local servers; those switch on the development-only setting that
allows private addresses, because local servers live on 127.0.0.1.
"""
import gzip
import io
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import requests
import urllib3
from django.test import SimpleTestCase
from requests.adapters import HTTPAdapter

from scanner import config, http
from scanner.checks import data_exposure, mass_assignment, misconfig
from scanner.engine import ScanFailed, preflight
from domains.verification import is_practice_target, verify_file

PUBLIC = "93.184.216.34"
PRIVATE = "10.0.0.5"


def addrinfo(*addresses):
    """What socket.getaddrinfo returns for the given addresses."""
    return [
        (socket.AF_INET6 if ":" in a else socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, 0))
        for a in addresses
    ]


def fake_response(status=200, headers=None, body=b""):
    response = requests.Response()
    response.status_code = status
    response.headers.update(headers or {})
    response.raw = urllib3.response.HTTPResponse(body=io.BytesIO(body), preload_content=False, status=status)
    return response


class FakeNetwork:
    """
    Replaces DNS and the actual sending, and records what would have gone out.
    `dns` maps a hostname to a list of address lists, one per lookup (the last
    one repeats), so a name can answer differently the second time.
    """

    def __init__(self, dns, responses):
        self.dns, self.responses = dns, list(responses)
        self.lookups, self.sent = {}, []

    def getaddrinfo(self, host, port, *args, **kwargs):
        answers = self.dns[host]
        n = self.lookups.get(host, 0)
        self.lookups[host] = n + 1
        return addrinfo(*answers[min(n, len(answers) - 1)])

    def send(self, adapter, request, **kwargs):
        self.sent.append(request)
        response = self.responses.pop(0) if self.responses else fake_response()
        response.request = request          # a real adapter does this
        return response

    def __enter__(self):
        self._patches = [
            mock.patch("socket.getaddrinfo", self.getaddrinfo),
            mock.patch.object(HTTPAdapter, "send", lambda adapter, request, **kw: self.send(adapter, request, **kw)),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()


def reason_of(call):
    try:
        call()
    except http.ScanRequestError as e:
        return e.reason
    return None


class AddressRulesTests(SimpleTestCase):
    def test_public_addresses(self):
        for address in ["8.8.8.8", "1.1.1.1", "93.184.216.34", "2606:4700:4700::1111",
                        "::ffff:8.8.8.8", "64:ff9b::808:808"]:
            self.assertTrue(http.is_public_address(address), address)

    def test_private_and_special_addresses(self):
        for address in ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.169.254",
                        "100.64.0.1", "0.0.0.0", "224.0.0.1", "192.0.2.1", "198.18.0.1",
                        "::1", "fe80::1", "fc00::1", "::",
                        "::ffff:127.0.0.1", "::ffff:10.0.0.1",
                        "64:ff9b::7f00:1", "2002:7f00:1::"]:
            self.assertFalse(http.is_public_address(address), address)


class ResolveTests(SimpleTestCase):
    def test_disguised_loopback_addresses_are_refused(self):
        # Every one of these is 127.0.0.1 written differently.
        for host in ["127.0.0.1", "2130706433", "0x7f.0.0.1", "017700000001", "127.1", "localhost", "::1"]:
            self.assertEqual(reason_of(lambda: http.resolve_public(host, 80)), "private", host)

    def test_one_private_address_among_public_ones_refuses_the_target(self):
        with FakeNetwork({"mixed.test": [[PUBLIC, PRIVATE]]}, []):
            self.assertEqual(reason_of(lambda: http.resolve_public("mixed.test", 80)), "private")

    def test_unknown_name(self):
        self.assertEqual(reason_of(lambda: http.resolve_public("no-such-host-shovll.invalid", 80)), "dns")

    def test_ipv4_is_preferred(self):
        with FakeNetwork({"dual.test": [["2606:4700:4700::1111", PUBLIC]]}, []):
            self.assertEqual(http.resolve_public("dual.test", 80), PUBLIC)

    def test_the_development_flag_allows_private_addresses(self):
        with mock.patch.dict(os.environ, {"SHOVL_ALLOW_PRIVATE_TARGETS": "1"}):
            self.assertEqual(http.resolve_public("127.0.0.1", 80), "127.0.0.1")
        with mock.patch.dict(os.environ, {"SHOVL_ALLOW_PRIVATE_TARGETS": "0"}):
            self.assertEqual(reason_of(lambda: http.resolve_public("127.0.0.1", 80)), "private")


class PinningTests(SimpleTestCase):
    def test_connects_to_the_checked_address_and_sends_the_real_host(self):
        with FakeNetwork({"example.test": [[PUBLIC]]}, [fake_response(body=b"hi")]) as net:
            response = http.get("https://example.test/path?q=1")
        sent = net.sent[0]
        self.assertEqual(sent.url, f"https://{PUBLIC}/path?q=1")
        self.assertEqual(sent.headers["Host"], "example.test")
        self.assertEqual(response.url, "https://example.test/path?q=1")      # the caller sees the name, not the address
        self.assertEqual(response.content, b"hi")

    def test_a_second_lookup_can_never_swap_in_a_private_address(self):
        # First answer public, every later answer private (DNS rebinding).
        with FakeNetwork({"rebind.test": [[PUBLIC], [PRIVATE]]}, [fake_response()]) as net:
            http.get("https://rebind.test/")
        self.assertEqual(net.lookups["rebind.test"], 1)
        self.assertEqual(net.sent[0].url, f"https://{PUBLIC}/")

    def test_ports_and_ipv6_addresses(self):
        with FakeNetwork({"example.test": [[PUBLIC]], "v6.test": [["2606:4700:4700::1111"]]},
                         [fake_response(), fake_response()]) as net:
            http.get("http://example.test:8080/x")
            http.get("https://v6.test/")
        self.assertEqual(net.sent[0].url, f"http://{PUBLIC}:8080/x")
        self.assertEqual(net.sent[0].headers["Host"], "example.test:8080")
        self.assertEqual(net.sent[1].url, "https://[2606:4700:4700::1111]/")

    def test_credentials_in_the_url_are_dropped(self):
        with FakeNetwork({"example.test": [[PUBLIC]]}, [fake_response()]) as net:
            http.get("http://user:secret@example.test/")
        self.assertNotIn("Authorization", net.sent[0].headers)
        self.assertNotIn("secret", net.sent[0].url)

    def test_private_targets_are_refused_before_anything_is_sent(self):
        with FakeNetwork({"internal.test": [[PRIVATE]]}, []) as net:
            self.assertEqual(reason_of(lambda: http.get("https://internal.test/")), "private")
        self.assertEqual(net.sent, [])

    def test_bad_urls(self):
        for url in ["not-a-url", "ftp://example.test/", "http://", "http://example.test:99999/"]:
            self.assertEqual(reason_of(lambda: http.get(url)), "invalid_url", url)

    def test_the_user_agent_is_sent_and_can_be_overridden(self):
        with FakeNetwork({"example.test": [[PUBLIC]]}, [fake_response(), fake_response()]) as net:
            http.get("http://example.test/")
            http.get("http://example.test/", headers={"User-Agent": "custom/1"})
        self.assertEqual(net.sent[0].headers["User-Agent"], http.USER_AGENT)
        self.assertEqual(net.sent[1].headers["User-Agent"], "custom/1")


class RedirectTests(SimpleTestCase):
    NAMES = {"example.test": [[PUBLIC]], "www.example.test": [[PUBLIC]], "evil.test": [[PUBLIC]]}

    def redirect(self, location, status=302):
        return fake_response(status, {"Location": location})

    def test_http_to_https_on_the_same_site(self):
        with FakeNetwork(self.NAMES, [self.redirect("https://example.test/"), fake_response(body=b"done")]) as net:
            response = http.get("http://example.test/")
        self.assertEqual(response.content, b"done")
        self.assertEqual(len(net.sent), 2)

    def test_relative_redirect(self):
        with FakeNetwork(self.NAMES, [self.redirect("/login"), fake_response(body=b"ok")]) as net:
            http.get("https://example.test/start")
        self.assertEqual(net.sent[1].url, f"https://{PUBLIC}/login")

    def test_www_counts_as_the_same_site_in_both_directions(self):
        with FakeNetwork(self.NAMES, [self.redirect("https://www.example.test/"), fake_response()]):
            http.get("https://example.test/")
        with FakeNetwork(self.NAMES, [self.redirect("https://example.test/"), fake_response()]):
            http.get("https://www.example.test/")

    def test_another_domain_is_stopped(self):
        with FakeNetwork(self.NAMES, [self.redirect("https://evil.test/")]) as net:
            self.assertEqual(reason_of(lambda: http.get("https://example.test/")), "redirect_offsite")
        self.assertEqual(len(net.sent), 1)

    def test_a_redirect_to_a_private_address_is_stopped(self):
        with FakeNetwork(self.NAMES, [self.redirect("http://169.254.169.254/latest/meta-data/")]) as net:
            self.assertEqual(reason_of(lambda: http.get("https://example.test/")), "redirect_offsite")
        self.assertEqual(len(net.sent), 1)

    def test_every_hop_is_checked_again(self):
        # Same site, but the name now resolves to a private address on the second hop.
        names = {"example.test": [[PUBLIC], [PRIVATE]]}
        with FakeNetwork(names, [self.redirect("https://example.test/next")]) as net:
            self.assertEqual(reason_of(lambda: http.get("http://example.test/")), "private")
        self.assertEqual(len(net.sent), 1)

    def test_a_redirect_loop_gives_up(self):
        with FakeNetwork(self.NAMES, [self.redirect("/loop") for _ in range(20)]) as net:
            self.assertEqual(reason_of(lambda: http.get("https://example.test/loop")), "redirects")
        self.assertEqual(len(net.sent), config.MAX_REDIRECTS + 1)

    def test_post_becomes_get_on_302_but_keeps_its_body_on_307(self):
        with FakeNetwork(self.NAMES, [self.redirect("/b", 302), fake_response()]) as net:
            http.post("https://example.test/a", json={"x": 1})
        self.assertEqual([r.method for r in net.sent], ["POST", "GET"])
        self.assertIsNone(net.sent[1].body)

        with FakeNetwork(self.NAMES, [self.redirect("/b", 307), fake_response()]) as net:
            http.post("https://example.test/a", json={"x": 1})
        self.assertEqual([r.method for r in net.sent], ["POST", "POST"])
        self.assertIn(b'"x"', net.sent[1].body)

    def test_a_redirect_without_a_location_is_just_a_response(self):
        with FakeNetwork(self.NAMES, [fake_response(302)]):
            self.assertEqual(http.get("https://example.test/").status_code, 302)


class TimeBudgetTests(SimpleTestCase):
    def test_spent_budget_sends_nothing(self):
        with FakeNetwork({"example.test": [[PUBLIC]]}, []) as net:
            self.assertEqual(reason_of(lambda: http.get("https://example.test/", budget=http.TimeBudget(0))), "time_limit")
        self.assertEqual(net.sent, [])

    def test_timeouts_are_clamped_to_what_is_left(self):
        seen = {}
        def send(adapter, request, **kw):
            seen["timeout"] = kw["timeout"]; return fake_response()
        with FakeNetwork({"example.test": [[PUBLIC]]}, []):
            with mock.patch.object(HTTPAdapter, "send", send):
                http.get("https://example.test/", budget=http.TimeBudget(2), timeout=(5, 15))
        connect, read = seen["timeout"]
        self.assertLessEqual(connect, 2)
        self.assertLessEqual(read, 2)


def start_server(handler, tls=None):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    server.handle_error = lambda request, client_address: None      # a client hanging up early is expected here
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(*tls)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/big":
            body = b"x" * (3 * 1024 * 1024)
            self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path == "/gzip":
            body = gzip.compress(b"\0" * (60 * 1024 * 1024))          # a few KB on the wire, 60 MB once unpacked
            self.send_response(200); self.send_header("Content-Encoding", "gzip"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path == "/chunked":
            self.send_response(200); self.send_header("Transfer-Encoding", "chunked"); self.end_headers()
            for part in (b"hello ", b"chunked ", b"world"):
                self.wfile.write(f"{len(part):x}\r\n".encode() + part + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
        elif self.path == "/trickle":
            self.send_response(200); self.send_header("Content-Length", "100"); self.end_headers()
            try:
                for _ in range(100):
                    self.wfile.write(b"."); self.wfile.flush(); time.sleep(0.2)
            except OSError:
                pass
        else:
            body = b'{"ok": true}'
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.do_GET()


@mock.patch.dict(os.environ, {"SHOVL_ALLOW_PRIVATE_TARGETS": "1"})
class ResponseHandlingTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = start_server(Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        super().tearDownClass()

    def test_a_normal_response_is_read_in_full(self):
        response = http.get(self.base + "/ok")
        self.assertEqual(response.json(), {"ok": True})
        self.assertFalse(response.truncated)

    def test_a_chunked_response_is_read_in_full(self):
        self.assertEqual(http.get(self.base + "/chunked").content, b"hello chunked world")

    def test_a_huge_response_is_cut_at_the_cap(self):
        response = http.get(self.base + "/big")
        self.assertEqual(len(response.content), config.MAX_BODY_BYTES)
        self.assertTrue(response.truncated)
        self.assertEqual(reason_of(lambda: http.require_complete(response)), "too_large")

    def test_a_compression_bomb_is_cut_at_the_cap_after_unpacking(self):
        started = time.time()
        response = http.get(self.base + "/gzip")
        self.assertEqual(len(response.content), config.MAX_BODY_BYTES)
        self.assertTrue(response.truncated)
        self.assertLess(time.time() - started, 5)

    def test_a_slow_trickle_is_cut_off(self):
        with mock.patch.object(config, "RESPONSE_TIME_CAP", 1.0):
            started = time.time()
            self.assertEqual(reason_of(lambda: http.get(self.base + "/trickle", timeout=(2, 5))), "timeout")
        self.assertLess(time.time() - started, 4)

    def test_a_trickle_cannot_outlast_the_scan_budget(self):
        started = time.time()
        self.assertEqual(reason_of(lambda: http.get(self.base + "/trickle", budget=http.TimeBudget(1.2), timeout=(2, 5))), "time_limit")
        self.assertLess(time.time() - started, 3)

    def test_environment_proxies_are_ignored(self):
        with mock.patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9"}):
            self.assertEqual(http.get(self.base + "/ok").status_code, 200)

    def test_headers_only_mode_does_not_read_the_body(self):
        response = http.get(self.base + "/big", read_body=False)
        self.assertEqual(response.status_code, 200)

    def test_without_the_development_flag_local_servers_are_private(self):
        with mock.patch.dict(os.environ, {"SHOVL_ALLOW_PRIVATE_TARGETS": "0"}):
            self.assertEqual(reason_of(lambda: http.get(self.base + "/ok")), "private")


@unittest.skipUnless(shutil.which("openssl"), "openssl is needed to make a test certificate")
@mock.patch.dict(os.environ, {"SHOVL_ALLOW_PRIVATE_TARGETS": "1"})
class TlsPinningTests(SimpleTestCase):
    """HTTPS to a pinned address must still verify the certificate against the real hostname."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dir = tempfile.mkdtemp()
        run = lambda *args, **kw: subprocess.run(args, cwd=cls.dir, check=True, capture_output=True, **kw)
        # Python 3.13 and later check certificates strictly by default: a CA
        # certificate must say it may sign certificates, and the server
        # certificate must say who issued it. So the test certificates carry
        # the standard extensions, as real ones do.
        with open(os.path.join(cls.dir, "ca.cnf"), "w") as f:
            f.write(
                "[req]\n"
                "distinguished_name = dn\n"
                "prompt = no\n"
                "x509_extensions = v3_ca\n"
                "[dn]\n"
                "CN = Shovll Test CA\n"
                "[v3_ca]\n"
                "subjectKeyIdentifier = hash\n"
                "authorityKeyIdentifier = keyid:always\n"
                "basicConstraints = critical, CA:TRUE\n"
                "keyUsage = critical, keyCertSign, cRLSign\n"
            )
        run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key", "-out", "ca.pem",
            "-days", "2", "-config", "ca.cnf")
        run("openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", "srv.key", "-out", "srv.csr", "-subj", "/CN=pinned.test")
        with open(os.path.join(cls.dir, "ext.cnf"), "w") as f:
            f.write(
                "subjectAltName = DNS:pinned.test\n"
                "basicConstraints = critical, CA:FALSE\n"
                "keyUsage = critical, digitalSignature, keyEncipherment\n"
                "extendedKeyUsage = serverAuth\n"
                "subjectKeyIdentifier = hash\n"
                "authorityKeyIdentifier = keyid:always\n"
            )
        run("openssl", "x509", "-req", "-in", "srv.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial",
            "-out", "srv.pem", "-days", "2", "-extfile", "ext.cnf")
        cls.ca = os.path.join(cls.dir, "ca.pem")
        cls.server = start_server(Handler, tls=(os.path.join(cls.dir, "srv.pem"), os.path.join(cls.dir, "srv.key")))
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        shutil.rmtree(cls.dir, ignore_errors=True)
        super().tearDownClass()

    def fake_dns(self):
        names = {"pinned.test": [["127.0.0.1"]], "other.test": [["127.0.0.1"]]}
        real = socket.getaddrinfo
        return mock.patch("socket.getaddrinfo", lambda host, *a, **kw: addrinfo(*names[host][0]) if host in names else real(host, *a, **kw))

    def test_the_certificate_is_checked_against_the_real_hostname(self):
        with self.fake_dns():
            response = http.get(f"https://pinned.test:{self.port}/ok", verify=self.ca)
        self.assertEqual(response.json(), {"ok": True})

    def test_a_certificate_for_a_different_name_is_rejected(self):
        with self.fake_dns():
            self.assertEqual(reason_of(lambda: http.get(f"https://other.test:{self.port}/ok", verify=self.ca)), "tls")

    def test_an_untrusted_certificate_is_rejected(self):
        with self.fake_dns():
            self.assertEqual(reason_of(lambda: http.get(f"https://pinned.test:{self.port}/ok")), "tls")


class PreflightTests(SimpleTestCase):
    """The reachability test that runs before any check."""

    def failure(self, url):
        try:
            preflight(url)
        except ScanFailed as e:
            return e.reason
        return None

    def test_a_private_target_fails_the_scan(self):
        with FakeNetwork({"internal.test": [[PRIVATE]]}, []):
            self.assertEqual(self.failure("https://internal.test/"), "private")

    def test_a_redirect_to_another_domain_fails_the_scan(self):
        names = {"example.test": [[PUBLIC]]}
        with FakeNetwork(names, [fake_response(302, {"Location": "https://elsewhere.test/"})]):
            self.assertEqual(self.failure("https://example.test/"), "redirect_offsite")

    def test_any_http_answer_counts_as_reachable(self):
        for status in (200, 404, 500):
            with FakeNetwork({"example.test": [[PUBLIC]]}, [fake_response(status)]):
                self.assertIsNone(self.failure("https://example.test/"), status)

    def test_an_unknown_name_fails_the_scan(self):
        self.assertEqual(self.failure("https://no-such-host-shovll.invalid/"), "dns")


@mock.patch.dict(os.environ, {"SHOVL_ALLOW_PRIVATE_TARGETS": "1"})
class CheckSizeCapTests(SimpleTestCase):
    """Checks that read the body say so when the size cap cut it short; the others carry on."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = start_server(Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        super().tearDownClass()

    def test_data_exposure_reports_a_too_large_response_as_an_error(self):
        result = data_exposure.run(self.base + "/big")
        self.assertEqual((result["severity"], result["reason"]), ("ERROR", "too_large"))
        self.assertEqual(result["detail"], [http.MESSAGES["too_large"]])

    def test_mass_assignment_reports_a_too_large_response_as_an_error(self):
        result = mass_assignment.run(self.base + "/big")
        self.assertEqual((result["severity"], result["reason"]), ("ERROR", "too_large"))

    def test_a_check_that_only_reads_headers_is_not_affected(self):
        self.assertNotEqual(misconfig.run(self.base + "/big")["severity"], "ERROR")

    def test_normal_responses_still_work(self):
        self.assertNotEqual(data_exposure.run(self.base + "/ok")["severity"], "ERROR")
        self.assertNotEqual(mass_assignment.run(self.base + "/ok")["severity"], "ERROR")


class PracticeTargetTests(SimpleTestCase):
    @mock.patch.dict(os.environ, {"SHOVL_ALLOW_PRIVATE_TARGETS": "0"})
    def test_production(self):
        for url in [
            "https://postman-echo.com/get",
            "https://api.postman-echo.com/get",
            "https://httpbingo.org/get",
            "https://jsonplaceholder.typicode.com/posts",
            "https://dummyjson.com/products",
        ]:
            self.assertTrue(is_practice_target(url), url)
        for url in ["http://localhost:8000/", "http://127.0.0.1/", "http://app.localhost/", "https://example.com/",
                    "https://typicode.com/", "https://my-app.typicode.com/"]:
            self.assertFalse(is_practice_target(url), url)

    @mock.patch.dict(os.environ, {"SHOVL_ALLOW_PRIVATE_TARGETS": "1"})
    def test_development(self):
        for url in ["http://localhost:8000/", "http://127.0.0.1:3000/", "https://postman-echo.com/"]:
            self.assertTrue(is_practice_target(url), url)

    def test_lookalikes_are_never_practice_targets(self):
        for url in ["https://postman-echo.com.evil.test/", "https://postman-echo.com@evil.test/",
                    "https://evilpostman-echo.com/", "http://localhost.evil.test/",
                    "https://dummyjson.com.evil.test/", "https://notdummyjson.com/",
                    "https://jsonplaceholder.typicode.com@evil.test/", "https://httpbingo.org.evil.test/"]:
            self.assertFalse(is_practice_target(url), url)


def sent_to(request):
    """(host, path) of a request: the URL holds the pinned address, the Host header the name."""
    return request.headers["Host"], urllib.parse.urlsplit(request.url).path


class FileVerificationTests(SimpleTestCase):
    TOKEN = "abc123token"
    NAMES = {"example.test": [[PUBLIC]], "www.example.test": [[PUBLIC]], "internal.test": [[PRIVATE]]}

    def verify(self, responses, hostname="example.test"):
        with FakeNetwork(self.NAMES, responses) as net:
            return verify_file(hostname, self.TOKEN), net

    def test_the_file_containing_exactly_the_token_verifies(self):
        self.assertTrue(self.verify([fake_response(body=self.TOKEN.encode())])[0])
        self.assertTrue(self.verify([fake_response(body=(self.TOKEN + "\n").encode())])[0])

    def test_the_token_somewhere_in_a_page_does_not_verify(self):
        page = f"<html>Not found: /shovl-verify-{self.TOKEN}.txt</html>".encode()
        self.assertFalse(self.verify([fake_response(404, body=page)])[0])
        self.assertFalse(self.verify([fake_response(200, body=page)])[0])        # a catch-all page that echoes the path
        self.assertFalse(self.verify([fake_response(body=f"token: {self.TOKEN}".encode())])[0])

    def test_a_missing_file_does_not_verify(self):
        self.assertFalse(self.verify([fake_response(404, body=b"nope")])[0])

    def test_private_hosts_are_never_fetched(self):
        ok, net = self.verify([fake_response(body=self.TOKEN.encode())], hostname="internal.test")
        self.assertFalse(ok)
        self.assertEqual(net.sent, [])

    def test_a_redirect_to_another_site_does_not_verify(self):
        ok, net = self.verify([fake_response(302, {"Location": "https://evil.test/"})])
        self.assertFalse(ok)
        # The new file name, then the old one, both on example.test; never the other site.
        self.assertEqual([sent_to(request) for request in net.sent], [
            ("example.test", f"/shovll-verify-{self.TOKEN}.txt"),
            ("example.test", f"/shovl-verify-{self.TOKEN}.txt"),
        ])

    def test_the_new_file_name_verifies_without_trying_the_old_one(self):
        ok, net = self.verify([fake_response(body=self.TOKEN.encode())])
        self.assertTrue(ok)
        self.assertEqual([sent_to(request) for request in net.sent], [("example.test", f"/shovll-verify-{self.TOKEN}.txt")])

    def test_a_domain_verified_with_the_old_file_name_still_verifies(self):
        # Verified before the rename to shovll: the file is still under the old name.
        ok, net = self.verify([fake_response(404, body=b"nope"), fake_response(body=self.TOKEN.encode())])
        self.assertTrue(ok)
        self.assertEqual(sent_to(net.sent[1]), ("example.test", f"/shovl-verify-{self.TOKEN}.txt"))

    def test_a_same_site_redirect_is_followed(self):
        self.assertTrue(self.verify([fake_response(301, {"Location": "https://www.example.test/shovl.txt"}),
                                     fake_response(body=self.TOKEN.encode())])[0])

    def test_hostnames_that_change_the_url_are_refused_without_a_request(self):
        for hostname in ["example.test@evil.test", "example.test?x=", "example.test#frag", "a.test\\b.test"]:
            ok, net = self.verify([fake_response(body=self.TOKEN.encode())], hostname=hostname)
            self.assertFalse(ok, hostname)
            self.assertEqual(net.sent, [], hostname)