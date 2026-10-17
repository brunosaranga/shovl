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

    // A scan run with "generate report" off opens on the summary view. The breakdown was saved
    // anyway, so opening it is free: no new scan.
    view: {
        note: "summary view: \"generate report\" was off for this scan, so the per-check breakdown is hidden. it was saved with the scan, so opening it doesn't use up a scan.",
        noteVerbose:
            "summary view: \"generate report\" was off for this scan, so the per-check breakdown and the raw responses are hidden. both were saved with the scan, so opening them doesn't use up a scan.",
        show: "show full report",
        hide: "back to summary",
    },

    // The summary view's fixes, when "suggest fix" was on.
    fixes: {
        title: "how to fix",
        lead: "one fix per problem, worst first. the full report has the evidence behind each one.",
        none: "nothing to fix: every check that ran passed.",
    },

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
