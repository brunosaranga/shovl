// Public APIs built for testing HTTP clients: free, no key, and their writes are
// echoed or simulated (never stored), so the practice scan's test POST is harmless.
// Practice targets skip domain ownership verification and are all a guest can scan.
//
// `host` mirrors ALLOWED_PRACTICE_TARGETS in backend domains/verification.py: keep both in sync.
// `example` is a path that answers directly; a bare domain may redirect to another site,
// which the scanner refuses (postman-echo.com/ does).
export const PRACTICE_TARGETS = [
    { host: "postman-echo.com", example: "https://postman-echo.com/get" },
    { host: "httpbingo.org", example: "https://httpbingo.org/get" },
    { host: "jsonplaceholder.typicode.com", example: "https://jsonplaceholder.typicode.com/posts" },
    { host: "dummyjson.com", example: "https://dummyjson.com/products" },
];

// Mirrors LOCAL_PRACTICE_TARGETS in the backend. Development builds only: in
// production these would point at our own server, so they are not practice targets.
const LOCAL_PRACTICE_TARGETS = ["localhost", "127.0.0.1"];

const PRACTICE_HOSTS = PRACTICE_TARGETS.map((target) => target.host);

const ACTIVE_PRACTICE_TARGETS = import.meta.env.DEV ? [...PRACTICE_HOSTS, ...LOCAL_PRACTICE_TARGETS] : PRACTICE_HOSTS;

// Pulls a bare hostname out of whatever the user typed. Tolerates input with or
// without a scheme ("api.example.com", "https://api.example.com/v1", etc.).
export function extractHostname(input) {
    if (!input) return "";
    let value = input.trim();
    if (!/^https?:\/\//i.test(value)) value = `https://${value}`;
    try {
        return new URL(value).hostname;
    } catch {
        return "";
    }
}

// Ensures a target_url has a scheme: the backend requires one.
export function normalizeTargetUrl(input) {
    if (!input) return "";
    const value = input.trim();
    return /^https?:\/\//i.test(value) ? value : `https://${value}`;
}

export function isPracticeTarget(input) {
    const hostname = extractHostname(input);
    if (!hostname) return false;
    return ACTIVE_PRACTICE_TARGETS.some((target) => hostname === target || hostname.endsWith(`.${target}`));
}

// How lists show a watched API: host (and port), path, and the query's parameter NAMES with
// their values masked, "api.example.com/v1?api_key=•••". Query strings often carry keys, and
// lists end up in screenshots and screen shares. The names stay because two addresses that
// differ only in their query are two different APIs to murindzi (backend watch/models.py,
// watch_key). Login details written into an address ("user:pass@host") are left out too.
export const MASK = "•••";

export function maskedTarget(url) {
    const raw = String(url || "");
    let parsed;
    try {
        parsed = new URL(raw);
    } catch {
        // Not a full address: drop the scheme and whatever follows "?" or "#".
        return raw.replace(/^https?:\/\//i, "").replace(/[?#].*$/, "").replace(/\/$/, "");
    }
    const path = parsed.pathname === "/" ? "" : parsed.pathname.replace(/\/$/, "");
    const names = parsed.search
        .slice(1)
        .split("&")
        .filter(Boolean)
        .map((part) => (part.includes("=") ? `${part.split("=")[0]}=${MASK}` : part));
    return `${parsed.host}${path}${names.length ? `?${names.join("&")}` : ""}`;
}
