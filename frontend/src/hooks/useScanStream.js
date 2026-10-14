import { useEffect, useRef, useState } from "react";
import { openScanStream } from "../lib/api";
import { describeResponse } from "../lib/apiErrors";
import { readEvents, readJsonBody } from "../lib/sse";
import { fill } from "../lib/text";
import { useContent } from "./useContent";

const MAX_LOG_LINES = 14;

// Runs one scan over GET /api/scans/stream/ and reports what happens.
//
//   phase:    "connecting" | "running" | "complete" | "failed" | "refused" | "error"
//   problem:  { kind: "refused" | "failed" | "error", code, message, retryAfter, scanId } or null
//
// Stream events from the backend, in order:
//   running (check: reachability), then running + result per check, then complete
//   result.severity can be ERROR: the check could not run (e.g. mass assignment on a real domain)
//   a scan that cannot produce a result sends error, then failed { scan_id, reason, message }
// A refusal (allowance, guest on a real domain, unverified domain) is a non-200 with a JSON body.
// restart() runs the same scan again (the "try again" button).
export function useScanStream({ options, enabled = true }) {
    const { scan, report, errors } = useContent();
    const [phase, setPhase] = useState("connecting");
    const [progress, setProgress] = useState(0);
    const [logs, setLogs] = useState(scan.terminal.boot);
    const [scanId, setScanId] = useState(null);
    const [problem, setProblem] = useState(null);

    const [runId, setRunId] = useState(0);
    const pausedRef = useRef(false);
    const controllerRef = useRef(null);

    const url = options?.url;
    const verbose = Boolean(options?.verbose);
    const suggestFix = Boolean(options?.suggest_fix);
    const generateReport = options?.generate_report !== false;

    useEffect(() => {
        if (!enabled || !url) return undefined;

        const controller = new AbortController();
        controllerRef.current = controller;
        let finished = false;

        const log = (line) => {
            if (pausedRef.current) return;
            setLogs((previous) => [...previous, line].slice(-MAX_LOG_LINES));
        };

        const track = (event) => {
            if (event.total) setProgress(Math.round((event.progress / event.total) * 100));
        };

        const handle = (event) => {
            if (event.status === "running") {
                log(fill(scan.terminal.running, { time: new Date().toLocaleTimeString(), check: event.check }));
                track(event);
            } else if (event.status === "result") {
                const severity = String(event.severity || "").toUpperCase();
                const detail = Array.isArray(event.detail) ? event.detail.join("; ") : event.detail || "";
                log(
                    fill(scan.terminal.result, {
                        check: event.check,
                        severity: report.severity[severity] || severity.toLowerCase(),
                        detail,
                    })
                );
                track(event);
            } else if (event.status === "error") {
                log(fill(scan.terminal.error, { check: event.check, message: event.message }));
            } else if (event.status === "failed") {
                finished = true;
                setPhase("failed");
                setScanId(event.scan_id ?? null);
                setProblem({
                    kind: "failed",
                    code: event.reason,
                    message: event.message || report.state.failed.text,
                    scanId: event.scan_id ?? null,
                });
            } else if (event.status === "complete") {
                finished = true;
                setProgress(100);
                setScanId(event.scan_id);
                setPhase("complete");
            }
        };

        const run = async () => {
            try {
                const response = await openScanStream(
                    { url, verbose, suggest_fix: suggestFix, generate_report: generateReport },
                    { signal: controller.signal }
                );

                if (!response.ok) {
                    const body = await readJsonBody(response);
                    const described = describeResponse(response.status, body, errors);
                    finished = true;
                    setPhase("refused");
                    setProblem({ kind: "refused", ...described });
                    return;
                }

                setPhase("running");
                for await (const event of readEvents(response)) {
                    handle(event);
                }

                if (!finished) {
                    setPhase("error");
                    setProblem({ kind: "error", code: "stream_ended", message: scan.problems.streamEnded });
                }
            } catch (error) {
                if (error.name === "AbortError") return;
                setPhase("error");
                setProblem({ kind: "error", code: "network", message: errors.network });
            }
        };

        // Started on the next tick: React's development double-mount unmounts straight away,
        // which cancels this timer, so dev never opens (and interrupts) a second scan.
        const timer = setTimeout(run, 0);
        return () => {
            clearTimeout(timer);
            controller.abort();
        };
    }, [enabled, runId, url, verbose, suggestFix, generateReport, scan, report, errors]);

    return {
        phase,
        isActive: Boolean(enabled && url) && (phase === "connecting" || phase === "running"),
        progress,
        logs,
        scanId,
        problem,
        setPaused: (value) => {
            pausedRef.current = value;
        },
        stop: () => controllerRef.current?.abort(),
        restart: () => {
            setPhase("connecting");
            setProgress(0);
            setLogs(scan.terminal.boot);
            setScanId(null);
            setProblem(null);
            setRunId((id) => id + 1);
        },
    };
}
