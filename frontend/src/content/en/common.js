// Copy shared across the whole app. Placeholders like {name} are filled by lib/text.js.
export const common = {
    brand: "shovl",
    tagline: "break your API before someone else does.",
    footer: "shovl beta engine: librana",
    logoAlt: "shovl logo",
    homeLabel: "shovl home",
    contactEmail: "brunoeasaranga@gmail.com", // support, password help, account deletion (used by the FAQ)
    loading: "loading...",

    // Overall risk score of a scan (backend: CRITICAL | HIGH | MEDIUM | LOW | INCOMPLETE)
    risk: {
        CRITICAL: "CRITICAL",
        HIGH: "HIGH",
        MEDIUM: "MEDIUM",
        LOW: "LOW",
        INCOMPLETE: "INCOMPLETE",
        none: "—",
    },

    // Scan status (backend: pending | running | complete | failed | interrupted)
    status: {
        pending: "queued",
        running: "scanning",
        complete: "completed",
        failed: "failed",
        interrupted: "interrupted",
    },

    didNotCount: "this scan did not count against your allowance.",

    theme: {
        toDark: "switch to dark mode",
        toLight: "switch to light mode",
    },

    sound: {
        mute: "mute sound",
        unmute: "turn sound on",
    },
};
