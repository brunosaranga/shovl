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
};

export const domainsApi = {
    list: () => client.get("/domains/"),
    add: (hostname) => client.post("/domains/", { hostname }),
    verify: (id) => client.post(`/domains/${id}/verify/`),
};

export const scansApi = {
    list: () => client.get("/scans/"),
    detail: (id) => client.get(`/scans/${id}/`),
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
