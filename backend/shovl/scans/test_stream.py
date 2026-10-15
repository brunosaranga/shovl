"""
Tests for the keep-alive lines the scan stream sends while a check is working.

Run with:  python manage.py test scans
"""
import time
from unittest.mock import patch

from django.test import SimpleTestCase

from scans import views


def slow(seconds, value):
    time.sleep(seconds)
    return value


def broken():
    raise ValueError("check failed")


class WhileWorkingTests(SimpleTestCase):
    def run_to_end(self, generator):
        """Collects what a `yield from` caller would see: the yielded lines and the returned value."""
        lines = []
        while True:
            try:
                lines.append(next(generator))
            except StopIteration as done:
                return lines, done.value

    def test_a_quick_check_sends_no_keep_alive(self):
        lines, result = self.run_to_end(views.while_working(slow, 0, "done"))
        self.assertEqual(lines, [])
        self.assertEqual(result, "done")

    def test_a_slow_check_sends_keep_alive_lines_then_its_result(self):
        with patch.object(views, "KEEP_ALIVE_SECONDS", 0.05):
            lines, result = self.run_to_end(views.while_working(slow, 0.3, "done"))
        self.assertGreaterEqual(len(lines), 3)
        self.assertTrue(all(line == ": keep-alive\n\n" for line in lines))
        self.assertEqual(result, "done")

    def test_the_check_error_reaches_the_caller(self):
        with self.assertRaises(ValueError):
            self.run_to_end(views.while_working(broken))

    def test_keep_alive_lines_are_comments_not_events(self):
        # A line that starts with ":" is a comment in the event-stream format, so browsers
        # and the frontend's reader (frontend/src/lib/sse.js) skip it.
        self.assertTrue(views.KEEP_ALIVE.startswith(":"))
        self.assertTrue(views.KEEP_ALIVE.endswith("\n\n"))

    def test_a_browser_leaving_does_not_wait_for_the_check(self):
        with patch.object(views, "KEEP_ALIVE_SECONDS", 0.05):
            generator = views.while_working(slow, 2, "late")
            self.assertEqual(next(generator), views.KEEP_ALIVE)
            started = time.monotonic()
            generator.close()
        self.assertLess(time.monotonic() - started, 1)
