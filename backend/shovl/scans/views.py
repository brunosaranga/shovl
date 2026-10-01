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
from scanner.engine import run_scan, CHECKS, _calculate_risk
from scanner.report import format_report
from reporter.generator import generate_pdf
import importlib


logger = logging.getLogger(__name__)



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
            raw = run_scan(target_url, verbose=verbose, suggest_fix=suggest_fix, generate_report=generate_report)
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
        
        except Exception as e:
            scan.status = "failed"
            scan.save()
            return Response(
                {"error": f"Scan failed: {str(e)}"},
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


        def event_stream():
            finished = False
            try:
                results = []
                for i, module_path in enumerate(CHECKS):
                    try:
                        module = importlib.import_module(module_path)
                        check_name = module_path.split('.')[-1]

                        # Running event (check started)
                        yield f"data: {json.dumps({'status': 'running', 'check': check_name, 'progress': i, 'total': total})}\n\n"

                        result = module.run(target_url, token, verbose)
                        results.append(result)

                        # Result event (check finished)
                        yield f"data: {json.dumps({'status': 'result', 'check': check_name, 'severity': result['severity'], 'detail': result['detail'], 'progress': i + 1, 'total': total})}\n\n"

                    except Exception as e:
                        yield f"data: {json.dumps({'status': 'error', 'check': module_path, 'message': str(e)})}\n\n"


                try:
                    raw = {
                        'target': target_url,
                        'total_checks': len(results),
                        'verbose': verbose,
                        'suggest_fix': suggest_fix,
                        'generate_report': generate_report,
                        'findings': results,
                        'risk_score': _calculate_risk(results),
                    }
                    report = format_report(raw)

                    scan.status = 'complete'
                    scan.risk_score = report['meta']['risk_score']
                    scan.results = report
                    scan.completed_at = timezone.now()

                    # A PDF problem should not throw away a finished scan.
                    if generate_report:
                        try:
                            os.makedirs('reports', exist_ok=True)
                            pdf_path = f"reports/scan_{scan.id}.pdf"
                            generate_pdf(report, pdf_path)
                            scan.pdf_path = pdf_path
                        except Exception:
                            logger.exception('PDF generation failed for scan %s', scan.id)

                    scan.save()
                except Exception as e:
                    # Failed scans do not count against the allowance.
                    scan.status = 'failed'
                    scan.save(update_fields=['status'])
                    finished = True
                    yield f"data: {json.dumps({'status': 'error', 'check': 'report', 'message': str(e)})}\n\n"
                    return

                finished = True
                yield f"data: {json.dumps({'status': 'complete', 'scan_id': scan.id, 'risk_score': report['meta']['risk_score']})}\n\n"

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


        # total = len(CHECKS)

        # def event_stream():
        #     results = []
        #     for i, module_path in enumerate(CHECKS):
        #         try:
        #             module = importlib.import_module(module_path)
        #             check_name = module_path.split('.')[-1]

        #             # Running event (check started)
        #             yield f"data: {json.dumps({'status': 'running', 'check': check_name, 'progress': i, 'total': total})}\n\n"

        #             result = module.run(target_url, token, verbose)
        #             results.append(result)

        #             # Result event (check finished)
        #             yield f"data: {json.dumps({'status': 'result', 'check': check_name, 'severity': result['severity'], 'detail': result['detail'], 'progress': i + 1, 'total': total})}\n\n"

        #         except Exception as e:
        #             yield f"data: {json.dumps({'status': 'error', 'check': module_path, 'message': str(e)})}\n\n"

        #     # Create scan record and generate PDF
        #     from scanner.report import format_report
        #     from reporter.generator import generate_pdf
        #     from .models import Scan

        #     raw = {
        #         'target': target_url,
        #         'total_checks': len(results),
        #         'verbose': verbose,
        #         'suggest_fix': suggest_fix,
        #         'generate_report': generate_report,
        #         'findings': results,
        #         'risk_score': _calculate_risk(results),
        #     }
        #     report = format_report(raw)

        #     scan = Scan.objects.create(
        #         user=request.user,
        #         target_url=target_url,
        #         verbose=verbose,
        #         suggest_fix=suggest_fix,
        #         status='complete',
        #         risk_score=report['meta']['risk_score'],
        #         results=report,
        #         completed_at=timezone.now()
        #     )

        #     pdf_path = f'reports/scan_{scan.id}.pdf'
        #     if generate_report:
        #         os.makedirs('reports', exist_ok=True)
        #         generate_pdf(report, pdf_path)
        #         scan.pdf_path = pdf_path
        #         scan.save()

        #     yield f"data: {json.dumps({'status': 'complete', 'scan_id': scan.id, 'risk_score': report['meta']['risk_score']})}\n\n"

        # return StreamingHttpResponse(
        #     event_stream(),
        #     content_type='text/event-stream'
        # )