// The scan-running page and its live terminal.
export const scan = {
    meta: "scanning | shovl",

    title: "digging deeper...",
    targeting: "Targeting: {target}",

    controls: {
        pause: "pause the live log",
        resume: "resume the live log",
        stop: "stop the scan",
        spinnerAlt: "scan active",
    },

    terminal: {
        boot: [">> initializing shovl engine...", ">> establishing secure tunnel..."],
        running: ">> [{time}] running {check}...",
        result: ">> {check} -> [{severity}] {detail}",
        error: ">> ERROR in {check}: {message}",
        complete: ">> scan complete! redirecting to vulnerability results...",
    },

    // Asked when someone tries to leave while the scan runs.
    leave: {
        title: "stop this scan?",
        text: "leaving stops the scan. stopped scans don't count against your allowance.",
        stay: "keep scanning",
        leave: "stop and leave",
    },

    problems: {
        failedTitle: "scan failed.",
        refusedTitle: "scan not started.",
        connectionTitle: "connection lost.",
        streamEnded: "the connection closed before the scan finished. it was marked as interrupted.",
        retryAt: "the next scan frees up at {time}.",
        actions: {
            retry: "try again",
            back: "back to start",
            register: "create a free account",
            verify: "verify this domain",
            dashboard: "go to dashboard",
        },
    },
};
