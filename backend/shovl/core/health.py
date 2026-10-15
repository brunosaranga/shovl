from django.http import HttpResponse

HEALTH_PATH = "/healthz"


class HealthCheckMiddleware:
    """
    Answers the host's health check at /healthz with a plain "ok", before the host-name
    check and the HTTPS redirect: the checker may call the server by its internal address
    and over plain HTTP. It does not touch the database, so a sleeping Neon database does
    not make the service look broken.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTH_PATH:
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)
