export const dashboard = {
    meta: "dashboard | shovll",
    pageTitle: "dashboard",

    stats: {
        active: "Active Scans",
        threats: "Threat Alerts",
        noThreats: "none",
        remaining: "Scans Left",
        remainingGuest: "{remaining} of {limit} free",
        remainingDay: "{remaining} of {limit} today",
        unlimited: "unlimited",
        threatChip: "{label}: {count}",
    },

    newScan: "+ new scan",
    listTitle: "your scans",
    loading: "loading scans...",
    loadFailed: "couldn't load your scans. refresh to try again.",
    empty: "no scans yet. paste a URL on the start page and dig deeper.",

    row: {
        toggle: "show scan details",
        watch: "watch", // a scheduled scan, run by shovll watch
        watchTitle: "a scheduled scan by shovll watch: it didn't count against your allowance",
        summary: "scan summary",
        counts: "{HIGH} high · {MEDIUM} medium · {LOW} low · {PASS} passed",
        coverage: "based on {run} of {total} checks.",
        view: "view vulnerability findings",
        running: "this scan is still running.",
        paused: "this scan is paused.",
        open: "open scan",
        interrupted: "the scan stopped before it finished, usually because the page was closed.",
        stopped: "this scan was stopped before it finished.",
    },

    guest: {
        title: "guest session",
        text: "guest scans are kept for 30 days. create a free account to keep them and to scan your own domains.",
        counting: "scans you run today still count toward today's total after you register.",
        cta: "create a free account",
    },
};
