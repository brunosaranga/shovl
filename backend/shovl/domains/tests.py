"""
DNS verification (domains/verification.py): the TXT record under the newest name, _xikomu-verify,
and, for domains verified before a rename, the older ones, _shovll-verify and _shovl-verify. The
file method's tests live in scanner/tests.py (FileVerificationTests), next to the request helper
they use.

Run with:  DJANGO_DEBUG=1 python manage.py test domains
"""
from unittest import mock

import dns.resolver
from django.test import SimpleTestCase

from domains import verification

TOKEN = "abc123token"

ALL_NAMES = [
    "_xikomu-verify.example.com",
    "_shovll-verify.example.com",
    "_shovl-verify.example.com",
]


def resolver(records):
    """A fake dns.resolver.resolve: `records` maps a record name to its TXT values."""
    asked = []

    def resolve(name, kind):
        asked.append(name)
        if name not in records:
            raise dns.resolver.NXDOMAIN()
        return [f'"{value}"' for value in records[name]]

    return resolve, asked


class DnsVerificationTests(SimpleTestCase):
    def check(self, records):
        resolve, asked = resolver(records)
        with mock.patch.object(dns.resolver, "resolve", side_effect=resolve):
            return verification.verify_dns("example.com", TOKEN), asked

    def test_the_new_record_name_verifies(self):
        ok, asked = self.check({"_xikomu-verify.example.com": [TOKEN]})
        self.assertTrue(ok)
        self.assertEqual(asked, ["_xikomu-verify.example.com"])

    def test_a_domain_verified_under_shovll_still_verifies(self):
        ok, asked = self.check({"_shovll-verify.example.com": [TOKEN]})
        self.assertTrue(ok)
        self.assertEqual(asked, ALL_NAMES[:2])

    def test_a_domain_verified_under_shovl_still_verifies(self):
        ok, asked = self.check({"_shovl-verify.example.com": [TOKEN]})
        self.assertTrue(ok)
        self.assertEqual(asked, ALL_NAMES)

    def test_no_record_does_not_verify(self):
        ok, asked = self.check({})
        self.assertFalse(ok)
        self.assertEqual(asked, ALL_NAMES)

    def test_a_record_with_another_token_does_not_verify(self):
        self.assertFalse(self.check({name: ["someone-else"] for name in ALL_NAMES})[0])

    def test_a_lookalike_record_name_does_not_count(self):
        self.assertFalse(self.check({
            "xikomu-verify.example.com": [TOKEN],
            "_xikomu.example.com": [TOKEN],
            "_xikomu-verify.example.com.evil.test": [TOKEN],
        })[0])
