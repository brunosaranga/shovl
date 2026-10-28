export const settings = {
    meta: "settings | xikomu",
    pageTitle: "settings",
    loadFailed: "couldn't load your watched APIs and domains. reload the page to try again.",

    account: {
        title: "account",
        email: "Email",
    },

    // murindzi: the account switch, the bell's mute, the emails and the watched APIs.
    watch: {
        title: "murindzi",
        switchLabel: "murindzi",
        about: "murindzi re-scans your API on a schedule and tells you when something gets worse.",
        on: "on",
        off: "off",
        plan: "Your plan",
        planLine: "watches {slots}, every {days} days",
        planUnlimited: "watches as many APIs as you like, every {days} days",
        one: "1 API",
        many: "{n} APIs",
        mute: "Mute the bell",
        muteNote: "news still lands in the bell; the badge only counts what needs you, and no alert emails go out.",
        email: "Email me alerts",
        emailNote: "when a watched API gets worse, or murindzi has to pause, we email {email}.",
        emailMuted: "the bell is muted, so no alert emails go out until you unmute it.",
        listTitle: "watched APIs",
        empty: "no watched APIs yet. scanning one of your verified domains starts one.",
        status: {
            watching: "watching · next scan {date}",
            switchedOff: "off for your account",
            off: "off",
            outOfPlan: "not in your plan",
            verification: "paused: verification no longer passes",
            failures: "paused: the last 3 scheduled scans failed",
        },
        toggle: "watch {target}",
        resume: "resume",
        verify: "verify domain",
        failed: "that didn't work. try again in a moment.",
    },

    domains: {
        title: "verified domains",
        empty: "no verified domains yet. scanning one of your own domains adds it here.",
        verified: "✓",
        verifiedLabel: "verified",
    },

    // Domains added on the verify page but never verified (plus any that lost verification).
    cache: {
        title: "unverified cache ({n})",
        lead: "domains you started verifying but didn't finish. removing one only forgets it here; you can always verify it again later.",
        empty: "empty: every domain you started verifying is verified.",
        remove: "remove",
        removeConfirm: "sure?",
        removeWatchConfirm: "sure? its watch goes too",
        emptyAll: "empty cache",
        emptyConfirm: "sure? remove all {n}",
        emptyWatchConfirm: "sure? remove all {n}, and their watches",
        busy: "removing...",
        failed: "that didn't work. try again in a moment.",
    },

    plan: {
        title: "subscription",
        plan: "Plan:",
        names: {
            free: "Free",
            pro: "Pro",
            staff: "Staff",
            guest: "Guest",
        },
        compare: "compare plans",
        scans: "Scans",
        remaining: "{remaining} of {limit} left today",
        unlimited: "unlimited",
    },
};
