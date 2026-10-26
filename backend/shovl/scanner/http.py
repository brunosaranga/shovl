"""
Shared request helper for the scanner checks.

Every check makes its requests through get() / post() here instead of calling
requests directly. That gives all of them the same rules:

  * Only public internet addresses. Every address a name resolves to is checked,
    and the connection goes to the address that was checked (no second lookup,
    so DNS rebinding cannot swap in a private one). HTTPS still verifies the
    certificate against the real hostname.
  * Redirects are followed one hop at a time, each hop going through the same
    checks, and only within the same site.
  * Response bodies are read in chunks, up to a size cap, under a time limit.
  * The same timeouts and total time budget for every check.
  * Plain-language errors that never contain hostnames, addresses or raw
    library error text.

Failures are raised as ScanRequestError, which is a kind of
requests.exceptions.RequestException, so the `except RequestException` in each
check keeps working.
"""
import ipaddress
import socket
import time
from contextlib import ExitStack
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter

from . import config

USER_AGENT = "xikomu-scanner/1.0 (API security self-check)"

# Not worth starting a new request with less than this left in the budget.
MIN_TIME_LEFT = 0.5

REDIRECT_STATUSES = (301, 302, 303, 307, 308)

MESSAGES = {
    "timeout": "The target took too long to respond.",
    "dns": "We couldn't find that address. Check that the domain name is spelled correctly.",
    "refused": "The target refused the connection.",
    "connection": "We couldn't connect to the target.",
    "tls": "The secure connection (HTTPS) to the target failed. Its certificate may be invalid or expired.",
    "redirects": "The target redirected too many times.",
    "redirect_offsite": "The target redirects to another domain. Scan that address directly if it's yours.",
    "private": "That address points to a private network, so we can't scan it.",
    "too_large": "The response was too large to inspect.",
    "invalid_url": "That URL isn't valid.",
    "bad_response": "The target sent a response we couldn't read.",
    "time_limit": "Skipped: the scan's time limit was reached.",
    "error": "The request to the target failed.",
}


class ScanRequestError(requests.exceptions.RequestException):
    """`reason` is a short code (see MESSAGES). str(error) is the plain-language message."""

    def __init__(self, reason, message=None):
        message = message or MESSAGES.get(reason, MESSAGES["error"])
        super().__init__(message)
        self.reason = reason
        self.message = message


class TimeBudget:
    """The total time a scan may spend making requests."""

    def __init__(self, seconds=None, clock=time.monotonic):
        self._clock = clock
        self.seconds = config.SCAN_TIME_BUDGET if seconds is None else seconds
        self._deadline = clock() + self.seconds

    def remaining(self):
        return max(self._deadline - self._clock(), 0.0)

    def extend(self, seconds):
        """Push the deadline back, e.g. by the time the scan spent paused, which is not scanning time."""
        self._deadline += max(seconds, 0.0)

    @property
    def expired(self):
        return self.remaining() < MIN_TIME_LEFT


# ---- errors ---------------------------------------------------------------------------

def _error_text(exc):
    """Everything the exception and its causes say, lowercased. Used for matching only, never shown."""
    parts, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        parts.append(str(exc))
        exc = exc.__cause__ or exc.__context__
    return " ".join(parts).lower()


def to_scan_error(exc):
    """Turn any requests exception into a ScanRequestError with a friendly message."""
    # Order matters: SSLError and the timeouts are subclasses of ConnectionError.
    if isinstance(exc, requests.exceptions.SSLError):
        return ScanRequestError("tls")
    if isinstance(exc, requests.exceptions.Timeout):
        return ScanRequestError("timeout")
    if isinstance(exc, requests.exceptions.TooManyRedirects):
        return ScanRequestError("redirects")
    if isinstance(exc, (requests.exceptions.InvalidURL,
                        requests.exceptions.MissingSchema,
                        requests.exceptions.InvalidSchema)):
        return ScanRequestError("invalid_url")
    if isinstance(exc, (requests.exceptions.ChunkedEncodingError,
                        requests.exceptions.ContentDecodingError)):
        return ScanRequestError("bad_response")
    if isinstance(exc, requests.exceptions.ConnectionError):
        text = _error_text(exc)
        if any(s in text for s in ("name or service not known", "failed to resolve",
                                   "nodename nor servname", "temporary failure in name resolution",
                                   "getaddrinfo failed", "no address associated")):
            return ScanRequestError("dns")
        if any(s in text for s in ("connection refused", "errno 111", "errno 61", "winerror 10061")):
            return ScanRequestError("refused")
        if "timed out" in text:
            return ScanRequestError("timeout")
        return ScanRequestError("connection")
    return ScanRequestError("error")


# ---- addresses ------------------------------------------------------------------------

_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _unwrap(ip):
    """An IPv6 address that just carries an IPv4 one (::ffff:127.0.0.1, 6to4, NAT64) is judged as that IPv4 address."""
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            return ip.ipv4_mapped
        if ip.sixtofour:
            return ip.sixtofour
        if ip in _NAT64:
            return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip


def is_public_address(address):
    """True only for ordinary public internet addresses."""
    ip = _unwrap(ipaddress.ip_address(address))
    return ip.is_global and not ip.is_multicast


def resolve_public(hostname, port):
    """
    Look the name up once and return the address to connect to.

    Every address the name resolves to must be public. If even one is not, the
    whole target is refused, so a name that mixes public and private addresses
    cannot be used to slip through. (The development flag lifts this rule.)
    """
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError):
        raise ScanRequestError("dns")

    allow_private = config.allow_private_targets()
    addresses = []
    for family, _, _, _, sockaddr in infos:
        address = sockaddr[0].split("%")[0]          # drop an IPv6 scope id such as fe80::1%eth0
        if not allow_private and not is_public_address(address):
            raise ScanRequestError("private")
        addresses.append((family, address))

    if not addresses:
        raise ScanRequestError("dns")

    # Prefer IPv4: many hosting networks have no IPv6 route.
    addresses.sort(key=lambda item: item[0] != socket.AF_INET)
    return addresses[0][1]


# ---- sending --------------------------------------------------------------------------

class _PinnedAdapter(HTTPAdapter):
    """Connects to the address in the URL, while HTTPS still checks the certificate against the real hostname."""

    def __init__(self, hostname, **kwargs):
        self._hostname = hostname
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["server_hostname"] = self._hostname
        pool_kwargs["assert_hostname"] = self._hostname
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


def _ascii_host(hostname):
    try:
        return hostname.encode("idna").decode("ascii")
    except UnicodeError:
        raise ScanRequestError("invalid_url")


def _send_once(stack, method, url, headers, timeout, **kwargs):
    """One request to one URL, with no redirect following. Returns the response with its body unread."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ScanRequestError("invalid_url")
    try:
        explicit_port = parts.port
    except ValueError:
        raise ScanRequestError("invalid_url")

    hostname = _ascii_host(parts.hostname)
    port = explicit_port or (443 if parts.scheme == "https" else 80)
    address = resolve_public(hostname, port)

    # Connect to the address we checked. The real name goes in the Host header
    # (and, for HTTPS, the certificate check). Credentials in the URL are dropped.
    literal = f"[{address}]" if ":" in address else address
    netloc = literal + (f":{explicit_port}" if explicit_port else "")
    pinned_url = urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, ""))

    host_header = f"[{hostname}]" if ":" in hostname else hostname
    if explicit_port:
        host_header += f":{explicit_port}"
    merged = dict(headers)
    merged["Host"] = host_header

    session = stack.enter_context(requests.Session())
    # A proxy would do its own lookup and skip the checks above.
    session.trust_env = False
    if parts.scheme == "https":
        session.mount("https://", _PinnedAdapter(hostname))

    response = session.request(
        method, pinned_url, headers=merged, timeout=timeout,
        allow_redirects=False, stream=True, **kwargs,
    )
    response.url = url        # the address the caller asked for, not the pinned one
    return response


def _same_site(first, second):
    """Same hostname, ignoring a leading "www." (so example.com and www.example.com are one site)."""
    def site(host):
        host = (host or "").lower().rstrip(".")
        return host[4:] if host.startswith("www.") else host
    return site(first) == site(second)


def _chunks(response):
    """
    Yield the body as it arrives. read1() returns whatever is available right
    now, so the time limits below are checked after every bit of data. A plain
    8 KB read would sit waiting for all 8 KB, and a target trickling one byte at
    a time could hold us far past the limit.
    """
    raw = response.raw
    if not hasattr(raw, "read1"):                      # older urllib3: no way to read "what is there"
        yield from response.iter_content(chunk_size=8192)
        return

    empty_reads = 0
    while True:
        chunk = raw.read1(8192, decode_content=True)
        if chunk:
            empty_reads = 0
            yield chunk
            continue
        empty_reads += 1
        if empty_reads >= 3 or getattr(raw, "closed", False):
            return


def _read_body(response, budget, max_bytes):
    """
    Read the body, up to max_bytes, under the time limits. Sets response.truncated
    when the cap cut it short. A slow target can overshoot the limits by at most
    one read timeout.
    """
    started = time.monotonic()
    chunks, size, truncated = [], 0, False

    for chunk in _chunks(response):
        size += len(chunk)
        if size > max_bytes:
            keep = len(chunk) - (size - max_bytes)
            if keep > 0:
                chunks.append(chunk[:keep])
            truncated = True
            break
        chunks.append(chunk)

        if budget is not None and budget.expired:
            raise ScanRequestError("time_limit")
        if time.monotonic() - started > config.RESPONSE_TIME_CAP:
            raise ScanRequestError("timeout")

    response.close()
    response._content = b"".join(chunks)
    response._content_consumed = True
    response.truncated = truncated


def require_complete(response):
    """For checks that parse the body: refuse a response that was cut short by the size cap."""
    if getattr(response, "truncated", False):
        raise ScanRequestError("too_large")


def request(method, url, *, budget=None, headers=None, timeout=None,
            read_body=True, max_bytes=None, **kwargs):
    """
    One request with the scanner's rules applied. Returns the response, or raises
    ScanRequestError. A 404 or 500 is a normal response, not an error.

    read_body=False returns as soon as the headers arrive (used by the
    reachability test). Otherwise the body is read, up to max_bytes, and
    response.truncated says whether it was cut short.
    """
    max_bytes = config.MAX_BODY_BYTES if max_bytes is None else max_bytes
    kwargs.pop("stream", None)
    kwargs.pop("allow_redirects", None)

    try:
        original_host = urlsplit(url).hostname
    except ValueError:
        raise ScanRequestError("invalid_url")

    current = url
    base_headers = {"User-Agent": USER_AGENT}
    base_headers.update(headers or {})

    with ExitStack() as stack:
        try:
            for hop in range(config.MAX_REDIRECTS + 1):
                connect, read = timeout or config.REQUEST_TIMEOUT
                if budget is not None:
                    if budget.expired:
                        raise ScanRequestError("time_limit")
                    # Never wait longer than the scan has left.
                    left = budget.remaining()
                    connect, read = min(connect, left), min(read, left)

                response = _send_once(stack, method, current, base_headers, (connect, read), **kwargs)

                location = response.headers.get("Location")
                if response.status_code in REDIRECT_STATUSES and location:
                    response.close()
                    if hop == config.MAX_REDIRECTS:
                        raise ScanRequestError("redirects")

                    following = urljoin(current, location)
                    if not _same_site(original_host, urlsplit(following).hostname):
                        raise ScanRequestError("redirect_offsite")

                    # Like a browser: 301, 302 and 303 turn a POST into a GET.
                    if response.status_code in (301, 302, 303) and method != "HEAD":
                        method = "GET"
                        kwargs = {k: v for k, v in kwargs.items() if k not in ("json", "data", "files")}
                    current = following
                    continue

                if read_body:
                    _read_body(response, budget, max_bytes)
                else:
                    response.close()
                return response

            raise ScanRequestError("redirects")
        except ScanRequestError:
            raise
        except requests.exceptions.RequestException as exc:
            raise to_scan_error(exc) from exc


def get(url, **kwargs):
    return request("GET", url, **kwargs)


def post(url, **kwargs):
    return request("POST", url, **kwargs)