import json
from rest_framework.renderers import BaseRenderer


class ServerSentEventRenderer(BaseRenderer):
    """Advertises text/event-stream so DRF content negotiation won't 406 the
    SSE scan stream. The streaming response is a raw StreamingHttpResponse, so
    this render() only runs for the occasional DRF Response (e.g. the gate's
    400/403 errors), which we JSON-encode so they stay readable."""
    media_type = 'text/event-stream'
    format = 'txt'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b''
        if isinstance(data, (dict, list)):
            return json.dumps(data).encode('utf-8')
        return str(data).encode('utf-8')