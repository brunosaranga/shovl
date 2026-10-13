# from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse, FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from .renderers import ServerSentEventRenderer
from django.utils import timezone
from urllib.parse import urlparse
import json, logging, os

from accounts.permissions import REGISTRATION_REQUIRED_MESSAGE
from .limits import AllowanceExceeded, start_scan
from .models import Scan
from .serializers import ScanSerializer
from domains.models import Domain
from domains.verification import is_practice_target
from scanner.engine import CHECKS, ScanFailed, build_raw, ensure_usable, preflight, run_check, run_scan
from scanner.http import TimeBudget
from scanner.report import format_report
from reporter.generator import generate_pdf

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


def mark_failed(scan, reason, message):
    """Save a failed scan with the reason, so the dashboard and report can say why. Failed scans do not count."""
    scan.status = 'failed'
    scan.results = {'error': {'reason': reason, 'message': message}}
    scan.completed_at = timezone.now()
    scan.save(update_fields=['status', 'results', 'completed_at'])


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

        # Validate URL provided
        if not target_url:
            return Response({"error": "target_url is required."}, status=400)
        
        # Validate URL format
        parsed = urlparse(target_url)
        if not parsed.scheme or not parsed.netloc:
            return Response(
                {"error": "Invalid URL format. Include http:// or https://"},
                status=status.HTTP_400_BAD_REQUEST
            )

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

            # Only spend the time/IO building a PDF when the user asked for one.
            # When skipped, pdf_path stays blank and ScanPDFView correctly 404s.
            if generate_report:
                pdf_path = f"reports/scan_{scan.id}.pdf"
                os.makedirs("reports", exist_ok=True)
                generate_pdf(report, pdf_path)
                scan.pdf_path = pdf_path

            scan.save()

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
    serializer_class = ScanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Scan.objects.filter(user=self.request.user)
    

class ScanPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            scan = Scan.objects.get(pk=pk, user=request.user)
        except Scan.DoesNotExist:
            return Response({'error': 'Scan not found.'}, status=404)
        
        if not scan.pdf_path or not os.path.exists(scan.pdf_path):
            return Response({'error': 'PDF not available.'}, status=404)
        
        response = FileResponse(
            open(scan.pdf_path, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="shovl_report_{pk}.pdf"'
        return response
    

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

        # target_url is required before any other check can run.
        if not target_url:
            return Response(
                {'error': 'target_url is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Same guards the blocking create endpoint enforces, applied before we
        # start streaming. Failures return a normal (non-stream) Response.
        parsed = urlparse(target_url)
        if not parsed.scheme or not parsed.netloc:
            return Response(
                {'error': 'Invalid URL format. Include http:// or https://'},
                status=status.HTTP_400_BAD_REQUEST
            )

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

            def fail(reason, message):
                """Mark the scan failed and tell the browser. The old 'error' event is sent too, so it shows in the log."""
                mark_failed(scan, reason, message)
                yield sse({'status': 'error', 'check': 'scan', 'message': message})
                yield sse({'status': 'failed', 'scan_id': scan.id, 'reason': reason, 'message': message})

            try:
                budget = TimeBudget()

                # Can we reach the target at all? Announced first, so the screen
                # is not silent while we wait.
                yield sse({'status': 'running', 'check': 'reachability', 'progress': 0, 'total': total})
                try:
                    preflight(target_url, budget=budget)
                except ScanFailed as e:
                    finished = True
                    yield from fail(e.reason, e.message)
                    return

                findings = []
                for i, module_path in enumerate(CHECKS):
                    check_name = module_path.split('.')[-1]

                    # Running event (check started)
                    yield sse({'status': 'running', 'check': check_name, 'progress': i, 'total': total})

                    # Never raises: a check that cannot run comes back as an ERROR finding.
                    result = run_check(module_path, target_url, token, verbose, budget=budget, allow_writes=allow_writes)
                    findings.append(result)

                    # Result event (check finished)
                    yield sse({
                        'status': 'result', 'check': check_name, 'severity': result['severity'],
                        'detail': result['detail'], 'progress': i + 1, 'total': total,
                    })

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

                    scan.status = 'complete'
                    scan.risk_score = report['meta']['risk_score']
                    scan.results = report
                    scan.completed_at = timezone.now()

                    # A PDF problem should not throw away a finished scan.
                    if generate_report:
                        try:
                            os.makedirs('reports', exist_ok=True)
                            pdf_path = f'reports/scan_{scan.id}.pdf'
                            generate_pdf(report, pdf_path)
                            scan.pdf_path = pdf_path
                        except Exception:
                            logger.exception('PDF generation failed for scan %s', scan.id)

                    scan.save()
                except Exception:
                    logger.exception('Building the report failed for scan %s', scan.id)
                    finished = True
                    yield from fail('report_error', 'We could not build the report for this scan.')
                    return

                finished = True
                yield sse({'status': 'complete', 'scan_id': scan.id, 'risk_score': report['meta']['risk_score']})

            finally:
                # The browser went away before the scan finished.
                # Interrupted scans do not count against the allowance.
                if not finished:
                    Scan.objects.filter(
                        pk=scan.pk, status__in=('pending', 'running')
                    ).update(status='interrupted')

        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )