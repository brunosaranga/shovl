// Copy shared across the whole app. Placeholders like {name} are filled by lib/text.js.
export const common = {
    brand: "xikomu",
    tagline: "break your API before someone else does.",
    footer: "xikomu beta engine: librana",
    logoAlt: "xikomu logo",
    homeLabel: "xikomu home",
    // Cloudflare Email Routing forwards both to Bruno's Gmail; replies come from there.
    // Support, password help, account deletion (FAQ, legal pages, pricing): {email} in copy.
    contactEmail: "support@xikomu.com",
    // Security problems in xikomu itself (privacy page, public/.well-known/security.txt):
    // {securityEmail} in copy.
    securityEmail: "security@xikomu.com",
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

    // Scan status (backend: pending | running | paused | complete | failed | interrupted | stopped)
    status: {
        pending: "queued",
        running: "scanning",
        paused: "paused",
        complete: "completed",
        failed: "failed",
        interrupted: "interrupted",
        stopped: "stopped",
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
