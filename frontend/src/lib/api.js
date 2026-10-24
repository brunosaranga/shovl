// Every request to the Django API goes through this file.
//   - attaches the stored token
//   - turns a 401 into "session expired" (once, in one place)
//   - groups the endpoints so components never build URLs
import axios from "axios";
import { accessToken, clearSession, readSession } from "./session";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const client = axios.create({
    baseURL: API_BASE_URL,
    headers: { "Content-Type": "application/json" },
});

/**
 * On the free hosting plan the API server sleeps after 15 idle minutes and takes about a
 * minute to wake. Called once when the app loads, so the server is already starting while
 * the visitor reads the page. The request itself is the wake-up call: the answer is not
 * needed (and, being cross-site with no-cors, not readable).
 */
export function wakeApi() {
    if (!API_BASE_URL) return;
    try {
        const healthUrl = new URL("/healthz", API_BASE_URL).href;
        fetch(healthUrl, { mode: "no-cors", cache: "no-store" }).catch(() => {});
    } catch {
        // VITE_API_BASE_URL is not a full address: nothing to wake.
    }
}

// Endpoints that must never carry the stored token, and whose 401 means
// "wrong credentials", not "session expired". An old token in the header would
// otherwise make Django reject the request before the view even runs.
const NO_AUTH = ["/accounts/login/", "/accounts/register/", "/accounts/guest/", "/accounts/token/refresh/"];
// Sends the guest token, but a 401 is handled by the caller (SessionContext.register).
const OWN_401 = ["/accounts/upgrade/"];

const matches = (url = "", list) => list.some((path) => url.includes(path));

// ---- session expiry ------------------------------------------------------
const expiryListeners = new Set();

/** Subscribe to "the stored token stopped working". Returns an unsubscribe function. */
export function onSessionExpired(listener) {
    expiryListeners.add(listener);
    return () => expiryListeners.delete(listener);
}

function expireSession(code) {
    const wasGuest = Boolean(readSession()?.isGuest);
    clearSession();
    expiryListeners.forEach((listener) => listener({ wasGuest, code }));
}

client.interceptors.request.use((config) => {
    const token = accessToken();
    if (token && !matches(config.url, NO_AUTH)) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

client.interceptors.response.use(
    (response) => response,
    (error) => {
        const url = error.config?.url;
        if (error.response?.status === 401 && !matches(url, NO_AUTH) && !matches(url, OWN_401)) {
            expireSession(error.response.data?.code);
        }
        return Promise.reject(error);
    }
);

// ---- endpoints -----------------------------------------------------------
export const accountsApi = {
    guest: () => client.post("/accounts/guest/", { tos_agreed: true }),
    login: (body) => client.post("/accounts/login/", body), // { email, password, guest_token? }
    register: (body) => client.post("/accounts/register/", body), // { email, password, tos_agreed }
    upgrade: (body) => client.post("/accounts/upgrade/", body), // guest token in the header
    me: () => client.get("/accounts/me/"),
    // The two switches only: { watch_enabled?, notifications_muted? }. Returns the /me/ body.
    updateMe: (body) => client.patch("/accounts/me/", body),
};

export const domainsApi = {
    list: () => client.get("/domains/"),
    add: (hostname) => client.post("/domains/", { hostname }),
    verify: (id) => client.post(`/domains/${id}/verify/`),
    // The unverified cache. Pending domains only: a verified one gets 409 { code: "domain_verified" }.
    remove: (id) => client.delete(`/domains/${id}/`),
    removePending: () => client.delete("/domains/pending/"), // 200 { removed }
};

// shovl watch (backend watch/views.py).
export const watchesApi = {
    list: () => client.get("/watches/"),
    // "watch this API" from a report: 201 started, 200 already watching, both { watch, state }
    // (state = the report's badge, refreshed). 409 { code: "plan_full", can_swap } when the
    // plan is full; send again with instead: true to swap on a one-slot plan.
    watch: (scanId, instead = false) => client.post("/watches/", { scan: Number(scanId), instead }),
    // Settings: turn one API on or off. 409 { code: "plan_full" } when turning on with no room.
    setActive: (id, active) => client.patch(`/watches/${id}/`, { active }),
    resume: (id) => client.post(`/watches/${id}/resume/`),
};

// The bell (backend notifications/views.py).
//   bell() → { badge, muted, needs_action: [...], news: [...], news_unread, has_more }
export const notificationsApi = {
    bell: (before) => client.get("/notifications/", { params: before ? { before } : undefined }),
    read: (id) => client.post(`/notifications/${id}/read/`),
    readAll: () => client.post("/notifications/read-all/"),
};

export const scansApi = {
    list: () => client.get("/scans/"),
    detail: (id) => client.get(`/scans/${id}/`),
    // A running scan's controls. 200 { id, status }; 409 { code: "scan_finished", status } once it ended.
    // Pause and stop take effect between two checks; the stream then sends "paused" or "stopped".
    pause: (id) => client.post(`/scans/${id}/pause/`),
    resume: (id) => client.post(`/scans/${id}/resume/`),
    // Short timeout: the page leaves right after, and an unanswered stop still ends the scan
    // when the stream closes (it is then marked interrupted instead).
    stop: (id) => client.post(`/scans/${id}/stop/`, null, { timeout: 5000 }),
    // The report as a PDF, built by the API on request. A Blob; lib/download.js saves it.
    // 409 { code: "scan_not_complete" }, 503 { code: "pdf_disabled" }, 429 too many.
    // A long timeout: the free API may be waking up.
    pdf: (id) => client.get(`/scans/${id}/pdf/`, { responseType: "blob", timeout: 90000 }),
    // "was this report useful?": any of { useful, comment, would_pay }. The first answer
    // needs `useful`. Returns { useful, comment, would_pay }.
    feedback: (id, body) => client.post(`/scans/${id}/feedback/`, body),
};

// ---- scan stream ---------------------------------------------------------
// Server-sent events need fetch(): axios can't stream, and EventSource can't send
// the Authorization header. Returns the raw Response; lib/sse.js reads it.
export async function openScanStream(options, { signal } = {}) {
    const params = new URLSearchParams({
        target_url: options.url,
        verbose: String(Boolean(options.verbose)),
        suggest_fix: String(Boolean(options.suggest_fix)),
        generate_report: String(options.generate_report !== false),
    });

    const token = accessToken();
    const response = await fetch(`${API_BASE_URL}/scans/stream/?${params}`, {
        headers: {
            Accept: "text/event-stream",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal,
    });

    if (response.status === 401) {
        let code;
        try {
            code = JSON.parse(await response.clone().text())?.code;
        } catch {
            code = undefined;
        }
        expireSession(code);
    }
    return response;
}

export default client;
