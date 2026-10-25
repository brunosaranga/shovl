// The scan-running page and its live terminal.
export const scan = {
    meta: "scanning | shovll",

    title: "digging deeper...",
    targeting: "Targeting: {target}",

    controls: {
        pause: "pause the scan",
        resume: "resume the scan",
        stop: "stop the scan",
        spinnerAlt: "scan active",
    },

    // Shown under the target while a pause is on its way, holding, or being undone.
    // The backend pauses between two checks, so the check in flight always finishes first.
    pauseState: {
        pausing: "pausing after the current check...",
        paused: "paused. nothing is sent to the target until you resume. after 5 minutes paused, the scan stops on its own.",
        resuming: "resuming...",
    },

    terminal: {
        boot: [">> initializing shovll engine...", ">> establishing secure tunnel..."],
        running: ">> [{time}] running {check}...",
        result: ">> {check} -> [{severity}] {detail}",
        error: ">> ERROR in {check}: {message}",
        paused: ">> [{time}] paused. nothing is sent until you resume.",
        resumed: ">> [{time}] resumed.",
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
        stoppedTitle: "scan stopped.",
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
