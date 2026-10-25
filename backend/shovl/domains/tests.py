"""
DNS verification (domains/verification.py): the TXT record under the new name, _shovll-verify,
and, for domains verified before the rename, the old one, _shovl-verify. The file method's
tests live in scanner/tests.py (FileVerificationTests), next to the request helper they use.

Run with:  DJANGO_DEBUG=1 python manage.py test domains
"""
from unittest import mock

import dns.resolver
from django.test import SimpleTestCase

from domains import verification

TOKEN = "abc123token"


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
        ok, asked = self.check({"_shovll-verify.example.com": [TOKEN]})
        self.assertTrue(ok)
        self.assertEqual(asked, ["_shovll-verify.example.com"])

    def test_a_domain_verified_with_the_old_record_name_still_verifies(self):
        ok, asked = self.check({"_shovl-verify.example.com": [TOKEN]})
        self.assertTrue(ok)
        self.assertEqual(asked, ["_shovll-verify.example.com", "_shovl-verify.example.com"])

    def test_no_record_does_not_verify(self):
        self.assertFalse(self.check({})[0])

    def test_a_record_with_another_token_does_not_verify(self):
        self.assertFalse(self.check({"_shovll-verify.example.com": ["someone-else"], "_shovl-verify.example.com": ["nope"]})[0])

    def test_a_lookalike_record_name_does_not_count(self):
        self.assertFalse(self.check({"shovll-verify.example.com": [TOKEN], "_shovll.example.com": [TOKEN]})[0])
