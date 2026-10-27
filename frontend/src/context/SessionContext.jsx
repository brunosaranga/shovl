import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { accountsApi, onSessionExpired } from "../lib/api";
import { clearSession, readSession, writeSession } from "../lib/session";

// Who is using xikomu right now, and the actions that change it.
//
//   status:  "anonymous" | "guest" | "unconfirmed" | "registered"
//            unconfirmed = an account whose email isn't confirmed yet: it only reaches the code
//            screen (/confirm-email) and the public pages (routes.jsx, AccessGate).
//   user:    the /accounts/me/ response ({ id, email, is_guest, allowance, email_confirmed,
//            confirmation }) once loaded, plus receivedAt (Date.now() when it arrived), so a
//            countdown the server gives in seconds (confirmation.resend_in) can be measured from it
//   ended:   why the last session ended, until a new one starts:
//            { reason: "expired", wasGuest, code } (the API rejected the token) or { reason: "logout" }
const SessionContext = createContext(null);

export function SessionProvider({ children }) {
    const [session, setSession] = useState(readSession);
    const [user, setUser] = useState(null);
    const [ended, setEnded] = useState(null);

    // A session stored before email confirmation existed has no `confirmed`: it counts as
    // unconfirmed until /me/ says otherwise (applyUser), so nothing opens by mistake.
    const status = !session ? "anonymous" : session.isGuest ? "guest" : session.confirmed === true ? "registered" : "unconfirmed";

    const save = useCallback((next) => {
        writeSession(next);
        setSession(next);
        setUser(null);
        setEnded(null);
    }, []);

    // The API layer reports a dead token (expired, revoked after an upgrade, account deleted).
    useEffect(
        () =>
            onSessionExpired((info) => {
                setSession(null);
                setUser(null);
                setEnded({ reason: "expired", ...info });
            }),
        []
    );

    // Store a /me/ response, and keep the stored guest and confirmed flags honest if the
    // server disagrees.
    const applyUser = useCallback((data) => {
        setUser({ ...data, receivedAt: Date.now() });
        const stored = readSession();
        const isGuest = Boolean(data.is_guest);
        const confirmed = Boolean(data.email_confirmed);
        if (stored && (stored.isGuest !== isGuest || stored.confirmed !== confirmed)) {
            const corrected = { ...stored, isGuest, confirmed };
            writeSession(corrected);
            setSession(corrected);
        }
        return data;
    }, []);

    const refreshUser = useCallback(async () => {
        if (!readSession()) return null;
        try {
            const { data } = await accountsApi.me();
            return applyUser(data);
        } catch {
            return null; // a 401 is already handled by the expiry listener
        }
    }, [applyUser]);

    // Load /me/ whenever the token changes (sign-in, upgrade, a new guest).
    const token = session?.access;
    useEffect(() => {
        if (!token) return undefined;
        let cancelled = false;
        accountsApi
            .me()
            .then(({ data }) => !cancelled && applyUser(data))
            .catch(() => {}); // a 401 is already handled by the expiry listener
        return () => {
            cancelled = true;
        };
    }, [token, applyUser]);

    /** First "dig deeper" on a practice target: create a guest account. Throws on 429. */
    const startGuestSession = useCallback(async () => {
        if (readSession()) return;
        const { data } = await accountsApi.guest();
        save({ access: data.access, isGuest: true });
    }, [save]);

    /** Email + password. A guest's scans move to the account (guest token goes in the body). */
    const signIn = useCallback(
        async ({ email, password }) => {
            const current = readSession();
            const body = { email, password };
            if (current?.isGuest) body.guest_token = current.access;
            const { data } = await accountsApi.login(body);
            save({ access: data.access, isGuest: false, confirmed: data.email_confirmed === true });
        },
        [save]
    );

    /**
     * New account (unconfirmed: the backend has just emailed it a code). A guest is upgraded in place (same account, scans stay attached) and the
     * old guest token stops working, so the new token MUST replace it, which save() does.
     */
    const register = useCallback(
        async ({ email, password }) => {
            const current = readSession();
            if (current?.isGuest) {
                try {
                    const { data } = await accountsApi.upgrade({ email, password, tos_agreed: true });
                    save({ access: data.access, isGuest: false, confirmed: false });
                    return { upgraded: true };
                } catch (error) {
                    if (error.response?.status !== 401) throw error;
                    // The guest token is no longer valid: register a fresh account instead.
                    clearSession();
                    setSession(null);
                }
            }
            await accountsApi.register({ email, password, tos_agreed: true });
            const { data } = await accountsApi.login({ email, password });
            save({ access: data.access, isGuest: false, confirmed: data.email_confirmed === true });
            return { upgraded: false };
        },
        [save]
    );

    const signOut = useCallback(() => {
        clearSession();
        setSession(null);
        setUser(null);
        setEnded({ reason: "logout", wasGuest: false });
    }, []);

    const value = useMemo(
        () => ({
            status,
            isGuest: status === "guest",
            isRegistered: status === "registered",
            user,
            allowance: user?.allowance ?? null,
            ended,
            refreshUser,
            // For answers that carry the /me/ body (the code screen's endpoints).
            applyUser,
            startGuestSession,
            signIn,
            register,
            signOut,
        }),
        [status, user, ended, refreshUser, applyUser, startGuestSession, signIn, register, signOut]
    );

    return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
    const ctx = useContext(SessionContext);
    if (!ctx) {
        throw new Error("useSession must be used inside <SessionProvider>");
    }
    return ctx;
}
