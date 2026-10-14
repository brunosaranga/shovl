// Where the sign-in token lives between visits. Nothing else touches localStorage
// for auth. Shape: { access: "<jwt>", isGuest: true | false }
//
// Storage can be unavailable (private mode, blocked site data), so every access is
// wrapped: the app still works for the visit, it just won't remember the session.

const KEY = "shovl.session";
const LEGACY_KEYS = ["access_token", "user"]; // what the old AuthContext wrote

function migrateLegacy() {
    // A token saved by the previous frontend belonged to a registered account
    // (guests did not exist yet). Adopt it once, then drop the old keys.
    const legacy = localStorage.getItem("access_token");
    LEGACY_KEYS.forEach((key) => localStorage.removeItem(key));
    if (!legacy) return null;
    const session = { access: legacy, isGuest: false };
    localStorage.setItem(KEY, JSON.stringify(session));
    return session;
}

export function readSession() {
    try {
        const raw = localStorage.getItem(KEY);
        if (!raw) return migrateLegacy();
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed.access === "string" ? parsed : null;
    } catch {
        return null;
    }
}

export function writeSession(session) {
    try {
        localStorage.setItem(KEY, JSON.stringify(session));
    } catch {
        // storage unavailable: the session still works until the tab closes
    }
}

export function clearSession() {
    try {
        localStorage.removeItem(KEY);
        LEGACY_KEYS.forEach((key) => localStorage.removeItem(key));
    } catch {
        // nothing stored, nothing to clear
    }
}

export function accessToken() {
    return readSession()?.access || null;
}
