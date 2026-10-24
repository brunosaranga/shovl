export const verify = {
    meta: "domain verification | shovl",
    pageTitle: "domain verification",

    settingUp: "setting up verification for {hostname}...",
    // Verify only (from the bell): no scan afterwards.
    verifyOnlyNote:
        "verifying only: no scan starts. if shovl watch was watching this domain, it picks up again once this passes. leave the record in place afterwards.",
    setupFailed: "setup failed.",

    title: "prove ownership.",
    target: "target:",
    step: "1. Add this TXT record to your DNS configuration:",
    labels: {
        host: "host / name:",
        type: "type:",
        value: "value:",
    },
    propagation: "Note: DNS propagation may take a few minutes. Make sure the record is active before verifying.",

    failedTitle: "verification failed.",
    failedReasons: [
        "DNS propagation can take up to 24 hours — wait a few minutes and retry.",
        "Make sure the record type is TXT, not CNAME or A.",
        "Make sure the host is exactly {record}.",
        "Check for typos in the value — copy it again using the button above.",
    ],

    action: {
        idle: "verify ownership",
        verifying: "verifying",
        verified: "verified.",
        retry: "retry",
    },
    copy: {
        idle: "copy",
        done: "copied!",
    },
    spinnerAlt: "verifying",
};
