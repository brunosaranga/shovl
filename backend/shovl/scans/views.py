# from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse, FileResponse
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from urllib.parse import urlparse
import json, os

from .models import Scan
from .serializers import ScanSerializer
from domains.models import Domain
from domains.verification import is_practice_target
from scanner.engine import run_scan, CHECKS
from scanner.report import format_report
from reporter.generator import generate_pdf
import importlib



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

        # Validate URL provided
        if not target_url:
            return Response({"error": "target_url is required."}, status=400)
        
        # Validate URL format
        parsed = urlparse(target_url)
        if not parsed.scheme or not parsed.netloc:
            return Response(
                {"error": "Invalied URL format. Include http:// or https://"}
            )
        
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
                })
            
        # Create scan record
        scan = Scan.objects.create(
            user=request.user,
            target_url=target_url,
            verbose=verbose,
            suggest_fix=suggest_fix,
            status="running"
        )

        try:
            raw = run_scan(target_url, verbose=verbose, suggest_fix=suggest_fix)
            report = format_report(raw)

            pdf_path = f"reports/scan_{scan.id}.pdf"
            os.makedirs("reports", exist_ok=True)
            generate_pdf(report, pdf_path)

            scan.status = "complete"
            scan.risk_score = report["meta"]["risk_score"]
            scan.results = report
            scan.pdf_path = pdf_path
            scan.completed_at = timezone.now()
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
    serializers_class = ScanSerializer
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
        
        response = FileReponse(
            open(scan.pdf_path, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="shovl_report={pk}.pdf'
        return Response
    

class ScanStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_url = request.query_params.get('target_url')
        token = request.query_params.get('token')
        verbose = request.query_params.get('verbose', 'false') == 'true'
        suggest_fix = request.query_params.get('suggest_fix', 'false') == 'true'

        if not target_url:
            return Response({'error': 'target_url required'}, status=400)
        
        total = len(CHECKS)

        def event_stream():
            results = []
            for i, module_path in enumerate(CHECKS):
                try:
                    module = importlib.import_module(module_path)
                    check_name = module_path.split('.')[-1]

                    # Running event
                    yield f"data: {json.dumps({'status': 'result', 'check': check_name, 'progress': i, 'total': total})}\n\n"

                    result = module.run(target_url, token, verbose)
                    results.append(result)

                    # Result event
                    yield f"data: {json.dumps({'status': 'running', 'check': check_name, 'severity': result['severity'], 'detail': result['detail'], 'progress': i + 1, 'total': total})}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'status': 'error', 'check': module_path, 'message': str(e)})}\n\n"

            # Create scan record and generate PDF
            from scanner.report import format_report
            from reporter.generator import generate_pdf
            from .models import Scan

            raw = {
                'target': target_url,
                'total_checks': len(results),
                'verbose': verbose,
                'suggest_fix': suggest_fix,
                'findings': results,
                'risk_score': 'HIGH',
            }
            report = format_report(raw)

            scan = Scan.objects.create(
                user=request.user,
                target_url=target_url,
                verbose=verbose,
                suggest_fix=suggest_fix,
                status='complete',
                risk_score=report['meta']['risk_score'],
                results=report,
                completed_at=timezone.now()
            )

            pdf_path = f'reports/scan_{scan.id}.pdf'
            os.makedirs('reports', exist_ok=True)
            generate_pdf(report, pdf_path)
            scan.pdf_path = pdf_path
            scan.save()

            yield f"data: {json.dumps({'status': 'complete', 'scan_id': scan.id, 'risk_score': report['meta']['risk_score']})}\n\n"

        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )