import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { useSession } from "./SessionContext";
import { accountsApi, domainsApi, notificationsApi, watchesApi } from "../lib/api";

// The bell's data and actions (backend notifications/). Layout renders the bell button,
// the modal and this provider; the mobile account menu opens the modal too.
//
// Registered accounts only: a guest can't verify a domain or watch an API, so their bell
// would always be empty. The data refreshes when the bell opens, on every page change and
// when the tab comes back into focus; nothing polls in the background.
//
//   bell:   the GET /api/notifications/ body, or null before the first load
//   status: "idle" | "loading" | "ready" | "error"
const NotificationsContext = createContext(null);

function readOne(bell, id) {
    const item = bell.news.find((entry) => entry.id === id);
    if (!item || item.read) return bell;
    const unread = Math.max(bell.news_unread - 1, 0);
    return {
        ...bell,
        news: bell.news.map((entry) => (entry.id === id ? { ...entry, read: true } : entry)),
        news_unread: unread,
        badge: bell.muted ? bell.badge : Math.max(bell.badge - 1, 0),
    };
}

function readEverything(bell) {
    return {
        ...bell,
        news: bell.news.map((entry) => ({ ...entry, read: true })),
        news_unread: 0,
        badge: bell.needs_action.length,
    };
}

export function NotificationsProvider({ children }) {
    const { status: sessionStatus, user, refreshUser } = useSession();
    // Whose bell this is: the data below is only shown to the account it was loaded for, so
    // signing out and in as someone else never flashes the previous person's bell.
    const owner = sessionStatus === "registered" ? user?.id ?? null : null;
    const enabled = owner !== null;
    const { pathname } = useLocation();
    // { owner, data, failed }: data is the GET /api/notifications/ body.
    const [state, setState] = useState({ owner: null, data: null, failed: false });
    const [open, setOpen] = useState(false);
    // Only the newest request may write: an older one finishing late must not win.
    const latest = useRef(0);

    const mine = state.owner === owner && enabled;
    const bell = mine ? state.data : null;
    const status = !enabled ? "idle" : bell ? "ready" : mine && state.failed ? "error" : "loading";
    const isOpen = open && enabled;

    const setBell = useCallback(
        (update) => setState((current) => ({ ...current, data: update(current.data) })),
        []
    );

    // Promise callbacks rather than async/await, like hooks/useScans.js: the state is only
    // ever set once the answer is in, never during the effect that asked for it.
    const refresh = useCallback(() => {
        if (!enabled) return Promise.resolve(null);
        const ticket = ++latest.current;
        return notificationsApi.bell().then(
            ({ data }) => {
                if (ticket === latest.current) setState({ owner, data, failed: false });
                return data;
            },
            () => {
                // Keep what's on screen; with nothing yet, the bell says it couldn't load.
                if (ticket === latest.current) {
                    setState((current) =>
                        current.owner === owner ? { ...current, failed: true } : { owner, data: null, failed: true }
                    );
                }
                return null;
            }
        );
    }, [enabled, owner]);

    // Every page change (and the first load, and a new account signing in).
    useEffect(() => {
        refresh();
    }, [refresh, pathname]);

    // Coming back to the tab.
    useEffect(() => {
        if (!enabled) return undefined;
        const onVisible = () => document.visibilityState === "visible" && refresh();
        document.addEventListener("visibilitychange", onVisible);
        return () => document.removeEventListener("visibilitychange", onVisible);
    }, [enabled, refresh]);

    const openBell = useCallback(() => {
        if (!enabled) return;
        setOpen(true);
        refresh();
    }, [enabled, refresh]);

    const closeBell = useCallback(() => setOpen(false), []);

    const loadOlder = useCallback(async () => {
        const last = bell?.news?.[bell.news.length - 1];
        if (!last) return;
        const { data } = await notificationsApi.bell(last.id);
        setBell((current) =>
            current ? { ...current, news: [...current.news, ...data.news], has_more: data.has_more } : current
        );
    }, [bell, setBell]);

    // Opening an item reads it. Shown as read at once; a failure just reloads the truth.
    const markRead = useCallback(
        async (id) => {
            setBell((current) => (current ? readOne(current, id) : current));
            try {
                await notificationsApi.read(id);
            } catch {
                refresh();
            }
        },
        [refresh, setBell]
    );

    const markAllRead = useCallback(async () => {
        setBell((current) => (current ? readEverything(current) : current));
        try {
            await notificationsApi.readAll();
        } catch {
            refresh();
        }
    }, [refresh, setBell]);

    // The account's mute, the same switch Settings shows. Throws, so the caller can say so.
    const setMuted = useCallback(
        async (muted) => {
            await accountsApi.updateMe({ notifications_muted: muted });
            await Promise.all([refresh(), refreshUser()]);
        },
        [refresh, refreshUser]
    );

    // The needs-action buttons. Each one reloads the bell, so a fixed item disappears.
    // They throw on failure, so the row can say so.
    const removeDomain = useCallback(
        async (domainId) => {
            await domainsApi.remove(domainId);
            await refresh();
        },
        [refresh]
    );

    const resumeWatch = useCallback(
        async (watchId) => {
            await watchesApi.resume(watchId);
            await refresh();
        },
        [refresh]
    );

    const value = useMemo(
        () => ({
            enabled,
            bell,
            status,
            badge: bell?.badge ?? 0,
            muted: Boolean(bell?.muted),
            isOpen,
            openBell,
            closeBell,
            refresh,
            loadOlder,
            markRead,
            markAllRead,
            setMuted,
            removeDomain,
            resumeWatch,
        }),
        [
            enabled,
            bell,
            status,
            isOpen,
            openBell,
            closeBell,
            refresh,
            loadOlder,
            markRead,
            markAllRead,
            setMuted,
            removeDomain,
            resumeWatch,
        ]
    );

    return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

export function useNotifications() {
    const ctx = useContext(NotificationsContext);
    if (!ctx) {
        throw new Error("useNotifications must be used inside <NotificationsProvider>");
    }
    return ctx;
}
