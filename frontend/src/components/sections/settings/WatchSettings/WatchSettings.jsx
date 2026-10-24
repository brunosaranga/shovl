import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useNotifications } from "../../../../context/NotificationsContext";
import { useSession } from "../../../../context/SessionContext";
import { useContent } from "../../../../hooks/useContent";
import { accountsApi, watchesApi } from "../../../../lib/api";
import { describeError } from "../../../../lib/apiErrors";
import { extractHostname } from "../../../../lib/targets";
import { fill, formatDate } from "../../../../lib/text";
import Breakable from "../../../ui/Breakable/Breakable";
import Switch from "../../../ui/Switch/Switch";
import styles from "./WatchSettings.module.css";

// "api.example.com/v1" for "https://api.example.com/v1/".
const shortTarget = (url) => String(url || "").replace(/^https?:\/\//i, "").replace(/\/$/, "");

// Which line a watched API gets, most important first.
function statusOf(watch, accountOn) {
    if (!accountOn) return { key: "switchedOff", tone: "off" };
    if (watch.paused_reason) return { key: watch.paused_reason, tone: "paused" };
    if (!watch.active) return { key: "off", tone: "off" };
    if (!watch.in_plan) return { key: "outOfPlan", tone: "off" };
    return { key: "watching", tone: "on" };
}

// One watched API: its own switch, plus "verify domain" or "resume" while it's paused. A
// paused watch keeps its slot, so the switch stays: turning it off frees the slot.
function WatchRow({ watch, accountOn, onChange }) {
    const { settings, errors } = useContent();
    const copy = settings.watch;
    const navigate = useNavigate();
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState(null);

    const target = shortTarget(watch.target_url);
    const status = statusOf(watch, accountOn);
    const label =
        status.key === "watching"
            ? fill(copy.status.watching, { date: formatDate(watch.next_run_at) })
            : copy.status[status.key] || copy.status.off;

    const act = async (request) => {
        setBusy(true);
        setProblem(null);
        try {
            await request();
            await onChange();
        } catch (error) {
            const described = describeError(error, errors);
            setProblem(described.status === 409 ? described.message : copy.failed);
        }
        setBusy(false);
    };

    const verify = () =>
        navigate("/verify", {
            state: { verifyOnly: true, hostname: extractHostname(watch.target_url), from: "/settings" },
        });

    return (
        <li className={styles.item} data-tone={status.tone}>
            <div className={styles.itemText}>
                <span className={styles.target}>
                    <Breakable text={target} />
                </span>
                <span className={styles.status}>
                    <span className={styles.dot} aria-hidden="true" />
                    {label}
                </span>
            </div>
            <div className={styles.controls}>
                {watch.paused_reason === "verification" ? (
                    <button type="button" className={styles.action} onClick={verify} disabled={busy}>
                        {copy.verify}
                    </button>
                ) : null}
                {watch.paused_reason === "failures" ? (
                    <button
                        type="button"
                        className={styles.action}
                        onClick={() => act(() => watchesApi.resume(watch.id))}
                        disabled={busy}
                    >
                        {copy.resume}
                    </button>
                ) : null}
                <Switch
                    checked={watch.active}
                    onChange={(next) => act(() => watchesApi.setActive(watch.id, next))}
                    label={fill(copy.toggle, { target })}
                    onText={copy.on}
                    offText={copy.off}
                    busy={busy}
                />
            </div>
            {problem ? (
                <p className={styles.problem} role="alert">
                    {problem}
                </p>
            ) : null}
        </li>
    );
}

// Settings → shovl watch: the account's switch (do scheduled scans run at all), the plan's
// line, the bell's mute (are you told), then each watched API with its own switch.
//   watches:  GET /api/watches/, or null while loading
//   onChange: reloads Settings' lists and the bell; returns a promise
export default function WatchSettings({ watches, onChange }) {
    const { settings, common } = useContent();
    const copy = settings.watch;
    const { user, refreshUser } = useSession();
    const { setMuted } = useNotifications();
    const [busy, setBusy] = useState(null); // "watch" | "mute" | null
    const [problem, setProblem] = useState(null);

    const accountOn = Boolean(user?.watch_enabled);
    const muted = Boolean(user?.notifications_muted);
    const plan = user?.plan;

    const flip = async (which, request) => {
        setBusy(which);
        setProblem(null);
        try {
            await request();
        } catch {
            setProblem(copy.failed);
        }
        setBusy(null);
    };

    const setAccountOn = (next) =>
        flip("watch", async () => {
            await accountsApi.updateMe({ watch_enabled: next });
            await Promise.all([refreshUser(), onChange()]);
        });

    let planText = common.loading;
    if (plan) {
        const days = plan.watch_cadence_days;
        if (plan.watch_slots === null || plan.watch_slots === undefined) {
            planText = fill(copy.planUnlimited, { days });
        } else {
            const slots = plan.watch_slots === 1 ? copy.one : fill(copy.many, { n: plan.watch_slots });
            planText = fill(copy.planLine, { slots, days });
        }
    }

    return (
        <div className={styles.watch}>
            <div className={styles.row}>
                <div className={styles.rowText}>
                    <span className={styles.label}>{copy.switchLabel}</span>
                    <span className={styles.note}>{copy.about}</span>
                </div>
                <Switch
                    checked={accountOn}
                    onChange={setAccountOn}
                    label={copy.switchLabel}
                    onText={copy.on}
                    offText={copy.off}
                    busy={busy === "watch"}
                    disabled={!user}
                />
            </div>

            <div className={styles.row}>
                <div className={styles.rowText}>
                    <span className={styles.label}>{copy.plan}</span>
                    <span className={styles.note}>{planText}</span>
                </div>
            </div>

            <div className={styles.row}>
                <div className={styles.rowText}>
                    <span className={styles.label}>{copy.mute}</span>
                    <span className={styles.note}>{copy.muteNote}</span>
                </div>
                <Switch
                    checked={muted}
                    onChange={(next) => flip("mute", () => setMuted(next))}
                    label={copy.mute}
                    onText={copy.on}
                    offText={copy.off}
                    busy={busy === "mute"}
                    disabled={!user}
                />
            </div>

            {problem ? (
                <p className={styles.problem} role="alert">
                    {problem}
                </p>
            ) : null}

            <div className={styles.listBlock}>
                <h3 className={styles.listTitle}>{copy.listTitle}</h3>
                {watches === null ? <p className={styles.empty}>{common.loading}</p> : null}
                {watches?.length === 0 ? <p className={styles.empty}>{copy.empty}</p> : null}
                {watches?.length ? (
                    <ul className={styles.list}>
                        {watches.map((watch) => (
                            <WatchRow key={watch.id} watch={watch} accountOn={accountOn} onChange={onChange} />
                        ))}
                    </ul>
                ) : null}
            </div>
        </div>
    );
}
