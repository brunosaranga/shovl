# from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.throttling import ScopedRateThrottle
from .renderers import ServerSentEventRenderer
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import json, logging, re, time

from accounts.permissions import REGISTRATION_REQUIRED_MESSAGE
from . import controls
from .compare import comparison_for
from .limits import AllowanceExceeded, start_scan
from .models import ACTIVE_STATUSES, Scan, ScanFeedback
from .serializers import FeedbackSerializer, ScanDetailSerializer, ScanSerializer
from .validators import target_url_error
from domains.models import Domain
from domains.verification import is_practice_target
from scanner.engine import CHECKS, ScanFailed, build_raw, ensure_usable, preflight, run_check, run_scan
from scanner.http import TimeBudget
from scanner.report import format_report
from reporter.generator import build_pdf
from watch.services import watch_after_scan

logger = logging.getLogger(__name__)

# Reasons that mean "we could not reach the target", as opposed to a scan that
# ran but produced nothing usable.
UNREACHABLE_REASONS = {
    'dns', 'refused', 'connection', 'timeout', 'tls', 'redirects', 'redirect_offsite', 'private',
    'bad_response', 'invalid_url',
}


def sse(payload):
    """One server-sent-events frame."""
    return f"data: {json.dumps(payload)}\n\n"


# A slow target can keep one check busy for most of the scan budget. Hosting proxies may
# close a connection that sends nothing for a minute, so the stream sends a comment line
# this often while it waits. Browsers and the frontend ignore comment lines.
KEEP_ALIVE_SECONDS = 15
KEEP_ALIVE = ": keep-alive\n\n"


def while_working(func, *args, **kwargs):
    """
    Runs func in a helper thread and yields KEEP_ALIVE until it finishes. Use with
    `result = yield from while_working(...)`: the result (or func's exception) comes back
    to the caller. If the browser leaves first, the check finishes in the background
    within the scan budget and its result is dropped.
    """
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(func, *args, **kwargs)
        while True:
            try:
                return future.result(timeout=KEEP_ALIVE_SECONDS)
            except TimeoutError:
                yield KEEP_ALIVE
    finally:
        pool.shutdown(wait=False)


def _sleep(seconds):
    """How a paused stream waits. A function of its own so tests can replace it."""
    time.sleep(seconds)


def hold_if_paused(scan_id, budget, pause):
    """
    Runs between two checks: this is where pause and stop take effect. Use with
    `state = yield from hold_if_paused(...)`. Returns "go" when the scan may carry on,
    otherwise the status that ends it (normally "stopped").

    While the scan is paused it yields a "paused" event, then keep-alive lines, and a
    "resumed" event when the person resumes. Time spent paused is given back to the scan's
    time budget and added to pause["seconds"]; past controls.MAX_PAUSE_SECONDS in total the
    scan is stopped, so a forgotten tab cannot hold a server thread for long.
    """
    status = controls.current_status(scan_id)
    if status == 'running':
        return 'go'
    if status != 'paused':
        return status

    yield sse({'status': 'paused', 'scan_id': scan_id})
    started = last_signal = time.monotonic()

    while True:
        _sleep(controls.PAUSE_POLL_SECONDS)
        now = time.monotonic()
        held = now - started
        status = controls.current_status(scan_id)

        if status == 'paused' and pause['seconds'] + held >= controls.MAX_PAUSE_SECONDS:
            # If it was resumed or stopped at this very moment, that answer stands instead.
            status = 'stopped' if controls.stop_paused_too_long(scan_id) else controls.current_status(scan_id)

        if status != 'paused':
            pause['seconds'] += held
            budget.extend(held)
            if status == 'running':
                yield sse({'status': 'resumed', 'scan_id': scan_id})
                return 'go'
            return status

        if now - last_signal >= KEEP_ALIVE_SECONDS:
            yield KEEP_ALIVE
            last_signal = now


def stopped_event(scan_id):
    """The last event of a scan that ended early, with the reason the report shows."""
    reason, message = controls.stop_details(scan_id)
    return sse({'status': 'stopped', 'scan_id': scan_id, 'reason': reason, 'message': message})


def mark_failed(scan, reason, message):
    """
    Save a failed scan with the reason, so the dashboard and report can say why. Failed scans do not count.
    Only a scan that has not ended yet is changed: if the person stopped it first, the stop stands.
    Returns True when the scan was marked failed.
    """
    return bool(
        Scan.objects.filter(pk=scan.pk, status__in=ACTIVE_STATUSES).update(
            status='failed',
            results={'error': {'reason': reason, 'message': message}},
            completed_at=timezone.now(),
        )
    )


def start_watch(scan_id):
    """
    murindzi: a manual scan just completed, so start watching its API if it qualifies
    (watch/services.py). A problem here is logged and never fails the scan.
    """
    try:
        watch_after_scan(Scan.objects.select_related('user').get(pk=scan_id))
    except Exception:
        logger.exception('Starting a watch failed for scan %s', scan_id)


# Create your views here.
class ScanListView(generics.ListAPIView):
    serializer_class = ScanSerializer

    def get_queryset(self):
        return Scan.objects.filter(user=self.request.user).order_by("-created_at")
    

class ScanCreateView(APIView):
    def post(self, request):
        target_url = request.data.get("target_url")
        verbose = request.data.get("verbose", False)
        suggest_fix = request.data.get("suggest_fix", False)
        generate_report = request.data.get("generate_report", True)

        # Present, http(s), not too long, nothing the database would refuse.
        error = target_url_error(target_url)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # Guests may only scan practice targets. Anything else needs a real
        # account. Checked before any domain lookup or network activity.
        if request.user.is_guest and not is_practice_target(target_url):
            return Response(REGISTRATION_REQUIRED_MESSAGE, status=status.HTTP_403_FORBIDDEN)
        
        # Check ToS agreement
        if not request.user.tos_agreed:
            return Response(
                {"error": "You must agree to the terms of service before scanning."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify ownership unless practice target
        if not is_practice_target(target_url):
            hostname = urlparse(target_url).hostname
            domain = Domain.objects.filter(
                user=request.user,
                hostname=hostname,
                verified=True
            ).first()

            if not domain:
                return Response({
                    "error": "Domain not verified.",
                    "detail": "Please verify ownership of this domain before scanning."
                }, status=status.HTTP_403_FORBIDDEN)
            
        # Check the allowance and create the scan record in one locked step.
        try:
            scan = start_scan(
                request.user,
                target_url=target_url,
                verbose=verbose,
                suggest_fix=suggest_fix,
            )
        except AllowanceExceeded as e:
            return Response(e.as_response_data(), status=e.http_status)

        try:
            # Checks that send data (the mass assignment POST) run on practice
            # targets only, never on a user's own domain.
            raw = run_scan(
                target_url,
                verbose=verbose,
                suggest_fix=suggest_fix,
                generate_report=generate_report,
                allow_writes=is_practice_target(target_url),
            )
            report = format_report(raw)

            scan.status = "complete"
            scan.risk_score = report["meta"]["risk_score"]
            scan.results = report
            scan.completed_at = timezone.now()
            # The PDF is built when someone downloads it (ScanPDFView), not here.
            scan.save()
            start_watch(scan.pk)

            return Response(ScanSerializer(scan).data, status=201)
        
        except ScanFailed as e:
            mark_failed(scan, e.reason, e.message)
            code = 'target_unreachable' if e.reason in UNREACHABLE_REASONS else 'scan_failed'
            return Response(
                {'detail': e.message, 'code': code, 'reason': e.reason},
                status=status.HTTP_502_BAD_GATEWAY
            )

        except Exception:
            logger.exception('Scan %s crashed', scan.id)
            message = 'The scan hit an unexpected problem.'
            mark_failed(scan, 'scan_error', message)
            return Response(
                {'detail': message, 'code': 'scan_failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ScanDetailView(generics.RetrieveAPIView):
    """One scan for the report page, with "since your last scan" and the feedback answer."""
    serializer_class = ScanDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Scan.objects.filter(user=self.request.user)


SCAN_NOT_FOUND = {'detail': 'Scan not found.', 'code': 'not_found'}
NOT_COMPLETE = {'detail': 'Only a finished scan has a report.', 'code': 'scan_not_complete'}


def pdf_filename(scan):
    """xikomu-report-<host>-<date>-<id>.pdf, in plain ASCII so every browser keeps it."""
    host = (urlparse(scan.target_url).hostname or 'api').lower()
    host = re.sub(r'[^a-z0-9.-]+', '-', host).strip('.-')[:60] or 'api'
    day = (scan.completed_at or scan.created_at).strftime('%Y-%m-%d')
    return f'xikomu-report-{host}-{day}-{scan.pk}.pdf'


def site_address():
    """The site's own address for the PDF's footer: the frontend's origin, without https://."""
    origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', None) or []
    return re.sub(r'^https?://', '', origins[0]) if origins else ''


class ScanPDFView(APIView):
    """
    GET /api/scans/<id>/pdf/: the report as a PDF download. The scan's owner only.

    Built in memory from the saved results on every download (reporter/generator.py), so
    nothing is written to disk and every finished scan has one, whichever knobs were on.

    200 application/pdf, with Content-Disposition naming the file
    404 {"detail", "code": "not_found"}: no such scan, or not yours
    409 {"detail", "code": "scan_not_complete"}: still running, failed, interrupted or stopped
    429: more than the "pdf" rate in settings (per person)
    503 {"detail", "code": "pdf_disabled"}: switched off with SHOVL_PDF_REPORTS=0
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'pdf'

    def perform_content_negotiation(self, request, force=False):
        # A client asking for application/pdf only would otherwise get a 406 before get() runs:
        # the PDF is returned as a plain response, and errors fall back to JSON.
        return super().perform_content_negotiation(request, force=True)

    def get(self, request, pk):
        scan = Scan.objects.filter(pk=pk, user=request.user).first()
        if scan is None:
            return Response(SCAN_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        if not settings.SHOVL_PDF_REPORTS:
            return Response(
                {'detail': 'PDF downloads are switched off for now.', 'code': 'pdf_disabled'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if scan.status != 'complete' or not isinstance(scan.results, dict):
            return Response(NOT_COMPLETE, status=status.HTTP_409_CONFLICT)

        try:
            data = build_pdf(
                scan.results,
                scan_id=scan.pk,
                target_url=scan.target_url,
                comparison=comparison_for(scan),
                site=site_address(),
            )
        except Exception:
            logger.exception('PDF for scan %s could not be built', scan.pk)
            return Response(
                {'detail': 'We could not build the PDF for this scan.', 'code': 'pdf_failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        Scan.objects.filter(pk=scan.pk).update(pdf_downloads=F('pdf_downloads') + 1)

        response = HttpResponse(data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename(scan)}"'
        response['Cache-Control'] = 'no-store'
        return response


def feedback_snapshot(scan, user):
    """What the report showed, copied onto the answer so it outlives the scan (see ScanFeedback)."""
    results = scan.results if isinstance(scan.results, dict) else {}
    meta = results.get('meta') or {}
    summary = results.get('summary') or {}
    return {
        'risk_score': scan.risk_score or meta.get('risk_score') or '',
        'summary': {key: value for key, value in summary.items() if isinstance(value, int)},
        'checks_run': meta.get('checks_run'),
        'total_checks': meta.get('total_checks'),
        'practice_target': is_practice_target(scan.target_url),
        'guest': bool(getattr(user, 'is_guest', False)),
        'options': {
            'generate_report': bool(meta.get('generate_report', True)),
            'suggest_fix': bool(meta.get('suggest_fix', scan.suggest_fix)),
            'verbose': bool(meta.get('verbose', scan.verbose)),
        },
    }


class ScanFeedbackView(APIView):
    """
    POST /api/scans/<id>/feedback/: the optional "was this report useful?" answer.
    Body: any of {"useful": true|false, "comment": "...", "would_pay": "yes"|"maybe"|"no"}.
    The first answer for a scan must include "useful"; later ones add to or change it.

    200 {"useful", "comment", "would_pay"} (201 the first time)
    400 field errors, or {"useful": [...]} when the first answer leaves it out
    404 no such scan, or not yours. 409 the scan didn't complete. 429 too many answers.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'feedback'

    def post(self, request, pk):
        scan = Scan.objects.filter(pk=pk, user=request.user).first()
        if scan is None:
            return Response(SCAN_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        if scan.status != 'complete':
            return Response(NOT_COMPLETE, status=status.HTTP_409_CONFLICT)

        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = serializer.validated_data

        with transaction.atomic():
            # Locks the scan row, so two answers sent at once can't both create one.
            Scan.objects.select_for_update().filter(pk=scan.pk).first()
            feedback = ScanFeedback.objects.filter(scan=scan).first()
            created = feedback is None
            if created:
                if 'useful' not in answer:
                    return Response(
                        {'useful': ['Say whether the report was useful first.']},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                feedback = ScanFeedback(scan=scan, **feedback_snapshot(scan, request.user))
            for field, value in answer.items():
                setattr(feedback, field, value)
            feedback.save()

        return Response(
            FeedbackSerializer(feedback).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ScanControlView(APIView):
    """
    POST /api/scans/<id>/pause/, /resume/ or /stop/ (no body). Only the scan's owner.

    200 {"id", "status"} once the scan is in the state asked for, including when it already was.
    409 {"detail", "code": "scan_finished", "status"} when it ended first (complete, failed,
    interrupted, stopped), so there is nothing left to pause, resume or stop.
    404 for a scan that doesn't exist or isn't yours.

    Pause and stop take effect between two checks: the stream sends "paused" or "stopped" then.
    A stop is recorded straight away, so the dashboard shows it at once.
    """
    permission_classes = [IsAuthenticated]
    control = None  # "pause", "resume" or "stop", set in urls.py

    def post(self, request, pk):
        if not Scan.objects.filter(pk=pk, user=request.user).exists():
            return Response({'detail': 'Scan not found.'}, status=status.HTTP_404_NOT_FOUND)

        now = controls.change(pk, self.control)
        if now == controls.TRANSITIONS[self.control][1]:
            return Response({'id': pk, 'status': now})

        return Response(
            {'detail': 'This scan has already finished.', 'code': 'scan_finished', 'status': now},
            status=status.HTTP_409_CONFLICT,
        )


class ScanStreamView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [ServerSentEventRenderer, JSONRenderer]

    def get(self, request):
        target_url = request.query_params.get('target_url')
        # Target-API tokens are deliberately NOT read from the query string:
        # URLs end up in proxy and access logs. Scans run unauthenticated for now.
        token = None
        verbose = request.query_params.get('verbose', 'false') == 'true'
        suggest_fix = request.query_params.get('suggest_fix', 'false') == 'true'
        generate_report = request.query_params.get('generate_report', 'true') == 'true'

        # Same guards the blocking create endpoint enforces, applied before we
        # start streaming. Failures return a normal (non-stream) Response.
        error = target_url_error(target_url)
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        parsed = urlparse(target_url)

        # Guests may only scan practice targets. This has to be answered here,
        # before streaming starts, because a started stream is already a 200.
        if request.user.is_guest and not is_practice_target(target_url):
            return Response(REGISTRATION_REQUIRED_MESSAGE, status=status.HTTP_403_FORBIDDEN)

        if not request.user.tos_agreed:
            return Response(
                {'error': 'You must agree to the terms of service before scanning.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not is_practice_target(target_url):
            hostname = parsed.hostname
            owns_verified_domain = Domain.objects.filter(
                user=request.user,
                hostname=hostname,
                verified=True
            ).exists()
            if not owns_verified_domain:
                return Response({
                    'error': 'Domain not verified.',
                    'detail': 'Please verify ownership of this domain before scanning.'
                }, status=status.HTTP_403_FORBIDDEN)


        # Counts the scan against the allowance and saves it as "running" now, not at the end,
        # so several streams opened together cannot all slip under the limit.
        # Refused here, before streaming starts.
        try:
            scan = start_scan(
                request.user,
                target_url=target_url,
                verbose=verbose,
                suggest_fix=suggest_fix,
            )
        except AllowanceExceeded as e:
            return Response(e.as_response_data(), status=e.http_status)

        total = len(CHECKS)

        # Checks that send data (the mass assignment POST) run on practice
        # targets only, never on a user's own domain.
        allow_writes = is_practice_target(target_url)

        def event_stream():
            finished = False
            pause = {'seconds': 0.0}  # time spent paused so far, all pauses added up

            def fail(reason, message):
                """Mark the scan failed and tell the browser. The old 'error' event is sent too, so it shows in the log.
                If the person stopped the scan first, the stop stands and the browser is told that instead."""
                if not mark_failed(scan, reason, message):
                    yield stopped_event(scan.id)
                    return
                yield sse({'status': 'error', 'check': 'scan', 'message': message})
                yield sse({'status': 'failed', 'scan_id': scan.id, 'reason': reason, 'message': message})

            try:
                budget = TimeBudget()

                # The scan's id comes first, so the page can pause or stop this scan.
                yield sse({'status': 'started', 'scan_id': scan.id, 'total': total})

                # Can we reach the target at all? Announced first, so the screen
                # is not silent while we wait.
                yield sse({'status': 'running', 'check': 'reachability', 'progress': 0, 'total': total})
                try:
                    yield from while_working(preflight, target_url, budget=budget)
                except ScanFailed as e:
                    finished = True
                    yield from fail(e.reason, e.message)
                    return

                findings = []
                for i, module_path in enumerate(CHECKS):
                    # Pause and stop take effect here, between two checks.
                    state = yield from hold_if_paused(scan.id, budget, pause)
                    if state != 'go':
                        finished = True
                        yield stopped_event(scan.id)
                        return

                    check_name = module_path.split('.')[-1]

                    # Running event (check started)
                    yield sse({'status': 'running', 'check': check_name, 'progress': i, 'total': total})

                    # Never raises: a check that cannot run comes back as an ERROR finding.
                    result = yield from while_working(
                        run_check, module_path, target_url, token, verbose, budget=budget, allow_writes=allow_writes
                    )
                    findings.append(result)

                    # Result event (check finished)
                    yield sse({
                        'status': 'result', 'check': check_name, 'severity': result['severity'],
                        'detail': result['detail'], 'progress': i + 1, 'total': total,
                    })

                # A pause or stop that arrived during the last check.
                state = yield from hold_if_paused(scan.id, budget, pause)
                if state != 'go':
                    finished = True
                    yield stopped_event(scan.id)
                    return

                # If no check produced a real result, the scan fails and does not count.
                try:
                    ensure_usable(findings)
                except ScanFailed as e:
                    finished = True
                    yield from fail(e.reason, e.message)
                    return

                try:
                    raw = build_raw(target_url, findings, verbose, suggest_fix, generate_report)
                    report = format_report(raw)

                    # Saved only while the scan has not ended: a stop that arrived in the
                    # last moments stands, and is never overwritten by "complete".
                    # The PDF is built when someone downloads it (ScanPDFView), not here.
                    saved = Scan.objects.filter(pk=scan.pk, status__in=ACTIVE_STATUSES).update(
                        status='complete',
                        risk_score=report['meta']['risk_score'],
                        results=report,
                        completed_at=timezone.now(),
                    )
                except Exception:
                    logger.exception('Building the report failed for scan %s', scan.id)
                    finished = True
                    yield from fail('report_error', 'We could not build the report for this scan.')
                    return

                finished = True
                if not saved:
                    yield stopped_event(scan.id)
                    return
                # Before "complete", so the report the page opens next already shows the watch.
                start_watch(scan.id)
                yield sse({'status': 'complete', 'scan_id': scan.id, 'risk_score': report['meta']['risk_score']})

            finally:
                # The browser went away before the scan finished (also while paused).
                # Interrupted scans do not count against the allowance. A stopped scan stays stopped.
                if not finished:
                    Scan.objects.filter(
                        pk=scan.pk, status__in=ACTIVE_STATUSES
                    ).update(status='interrupted')

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        # Proxies must pass each event on as soon as it is written, not collect the stream first.
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response