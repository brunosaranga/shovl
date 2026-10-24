import { useEffect, useId, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useNotifications } from "../../../../context/NotificationsContext";
import { useContent } from "../../../../hooks/useContent";
import { scansApi, watchesApi } from "../../../../lib/api";
import { describeError } from "../../../../lib/apiErrors";
import { extractHostname } from "../../../../lib/targets";
import { fill, formatDate } from "../../../../lib/text";
import styles from "./WatchBadge.module.css";

const CONFIRM_MS = 4000;
const HOVER = "(hover: hover)";

// The line under the report's top strip: is this API being watched (shovl watch), and if not,
// why, with the one button that fixes it. The API decides both (GET /api/scans/<id>/ → watch:
// { status, reason, action, next_run_at, cadence_days, watch_slots }); nothing shows for
// practice targets and guests (watch: null).
//
// The (i) explains shovl watch. It opens on click or tap and stays open until clicked again,
// Escape or a click elsewhere; with a mouse it also opens while hovered.
export default function WatchBadge({ scanId, targetUrl, initial }) {
    const { report, errors } = useContent();
    const copy = report.watch;
    const bell = useNotifications();
    const navigate = useNavigate();
    const { pathname } = useLocation();
    const infoId = useId();
    const wrapperRef = useRef(null);

    const [state, setState] = useState(initial);
    const [pinned, setPinned] = useState(false);
    const [hovered, setHovered] = useState(false);
    const [phase, setPhase] = useState("idle"); // idle | confirm | busy
    const [problem, setProblem] = useState(null);

    // The (i): Escape and a click outside close it.
    useEffect(() => {
        if (!pinned) return undefined;
        const onPointer = (event) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) setPinned(false);
        };
        const onKey = (event) => {
            if (event.key === "Escape") {
                setPinned(false);
                setHovered(false);
            }
        };
        document.addEventListener("mousedown", onPointer);
        document.addEventListener("keydown", onKey);
        return () => {
            document.removeEventListener("mousedown", onPointer);
            document.removeEventListener("keydown", onKey);
        };
    }, [pinned]);

    // "watch this one instead" waits for a second click, then forgets it.
    useEffect(() => {
        if (phase !== "confirm") return undefined;
        const timer = setTimeout(() => setPhase("idle"), CONFIRM_MS);
        return () => clearTimeout(timer);
    }, [phase]);

    if (!state) return null;

    const hover = (on) => {
        if (window.matchMedia(HOVER).matches) setHovered(on);
    };

    const act = async (request) => {
        setPhase("busy");
        setProblem(null);
        try {
            const next = await request();
            setState(next);
            bell.refresh();
        } catch (error) {
            const described = describeError(error, errors);
            setProblem(described.status === 409 ? described.message : copy.failed);
        }
        setPhase("idle");
    };

    const watch = (instead) => act(async () => (await watchesApi.watch(scanId, instead)).data.state);
    const resume = () =>
        act(async () => {
            await watchesApi.resume(state.watch_id);
            return (await scansApi.detail(scanId)).data.watch;
        });
    const verify = () =>
        navigate("/verify", { state: { verifyOnly: true, hostname: extractHostname(targetUrl), from: pathname } });

    const { status, reason, action } = state;
    const key = status === "watching" ? "watching" : reason;
    let label = copy.states[key] || copy.states.not_started;
    if (reason === "plan_full" && state.watch_slots === 1) label = copy.states.plan_full_one;
    label = fill(label, { n: state.watch_slots });

    const busy = phase === "busy";
    let button = null;
    if (reason === "unverified" || (status === "paused" && reason === "verification")) {
        button = { text: copy.actions.verify, onClick: verify };
    } else if (action === "watch") {
        button = { text: copy.actions.watch, onClick: () => watch(false) };
    } else if (action === "swap") {
        button = {
            text: phase === "confirm" ? copy.actions.swapConfirm : copy.actions.swap,
            onClick: () => (phase === "confirm" ? watch(true) : setPhase("confirm")),
        };
    } else if (action === "resume") {
        button = { text: copy.actions.resume, onClick: resume };
    } else if (action === "settings") {
        button = { text: copy.actions.settings, onClick: () => navigate("/settings") };
    }

    const open = pinned || hovered;
    const watching = status === "watching";

    return (
        <div className={styles.strip} data-status={status}>
            <div className={styles.line} ref={wrapperRef} onMouseEnter={() => hover(true)} onMouseLeave={() => hover(false)}>
                <span className={styles.dot} aria-hidden="true" />
                <span className={styles.label}>{label}</span>
                <button
                    type="button"
                    className={styles.info}
                    aria-label={copy.info}
                    title={copy.info}
                    aria-expanded={open}
                    aria-controls={infoId}
                    onClick={() => setPinned((value) => !value)}
                >
                    i
                </button>
                {open ? (
                    <div id={infoId} className={styles.popover} role="note">
                        <p>{fill(copy.about, { days: state.cadence_days })}</p>
                        {watching && state.next_run_at ? (
                            <p>{fill(copy.next, { date: formatDate(state.next_run_at) })}</p>
                        ) : null}
                        {reason === "plan_full" || reason === "over_plan" ? <p>{copy.whyOne}</p> : null}
                        {action === "swap" ? <p>{copy.swapNote}</p> : null}
                        <p>{copy.record}</p>
                        <p>{copy.settings}</p>
                    </div>
                ) : null}
            </div>

            {button ? (
                <button type="button" className={styles.action} onClick={button.onClick} disabled={busy}>
                    {busy ? copy.actions.busy : button.text}
                </button>
            ) : null}

            {problem ? (
                <p className={styles.problem} role="alert">
                    {problem}
                </p>
            ) : null}
        </div>
    );
}
