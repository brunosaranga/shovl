// The bell (layout/Bell). Titles and summaries of the items themselves come from the API
// (plain language, safe to show as they are); this is everything around them.
export const notifications = {
    open: "notifications",
    openWithCount: "notifications, {count} new",
    title: "notifications",
    close: "close notifications",
    menuItem: "notifications", // mobile account menu

    mute: "mute notifications",
    unmute: "unmute notifications",
    mutedNote: "muted: news still lands here, but the badge only counts what needs you.",
    readAll: "mark all read",

    needsTitle: "needs action",
    needsEmpty: "nothing needs you right now.",
    newsTitle: "news",
    newsEmpty: "no news yet. when murindzi starts on one of your APIs, you'll hear about it here.",
    older: "show older",
    loading: "loading...",
    failed: "couldn't load notifications. they'll try again when you change page.",
    actionFailed: "that didn't work. try again in a moment.",

    // The info line under a needs-action item's title.
    kinds: {
        domain_lost_verification: "verification lost · watch paused",
        domain_pending: "verification not finished",
        watch_paused: "scheduled scans failing",
    },
    unread: "new",

    actions: {
        verify: "verify domain",
        remove: "remove from unverified cache",
        removeConfirm: "sure? remove it",
        removeWatchesConfirm: "sure? its watch goes too",
        removing: "removing...",
        resume: "resume watch",
        resuming: "resuming...",
        openReport: "open report",
        settings: "murindzi settings",
    },

    // Inside an expanded alert.
    alert: {
        risk: "risk",
        changes: "what changed",
        change: {
            new: "new problem",
            worse: "worse",
        },
    },
};
