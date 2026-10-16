export const report = {
    meta: "report | shovl",
    pageTitle: "report",

    loading: "loading report...",
    notFound: "Report not found.",
    loadFailed: "Failed to load report.",

    labels: {
        target: "target: ",
        runtime: "runtime: ",
        risk: "risk score: ",
    },

    rerun: "re-run scan",
    rerunFull: "re-run with full report",
    summaryOnly: "summary only — the full findings breakdown was skipped because \"generate report\" was off for this scan.",

    coverage: {
        partial: "based on {run} of {total} checks.",
        incomplete: "0 of {total} checks completed — shovl couldn't assess this target. re-run the scan.",
        notRunTitle: "checks that could not run:",
    },

    matrix: {
        HIGH: "High",
        MEDIUM: "Medium",
        LOW: "Low",
        PASS: "Passed",
        ERROR: "Errors",
    },

    // Badge on each finding. ERROR means the check could not run, not that something was found.
    severity: {
        HIGH: "high",
        MEDIUM: "medium",
        LOW: "low",
        PASS: "pass",
        ERROR: "could not run",
    },

    findings: {
        title: "vulnerability findings",
        expandAll: "expand all",
        collapseAll: "collapse all",
        empty: "No findings returned for this scan.",
        noDetail: "No additional detail.",
        raw: "Raw response data (verbose)",
        remediation: "remediation suggestion:",
    },

    // Scans that are not complete.
    state: {
        running: {
            title: "still digging.",
            text: "this scan is still running. this page updates when it finishes.",
        },
        paused: {
            title: "scan paused.",
            text: "this scan is paused on its scan page. this page updates when it resumes or ends.",
        },
        failed: {
            title: "scan failed.",
            text: "the scan could not produce a result.",
        },
        interrupted: {
            title: "scan interrupted.",
            text: "the scan stopped before it finished, usually because the page was closed.",
        },
        stopped: {
            title: "scan stopped.",
            text: "this scan was stopped before it finished.",
        },
    },
};
