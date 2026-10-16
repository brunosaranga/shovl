import Spinner from "../../../ui/Spinner/Spinner";
import { useContent } from "../../../../hooks/useContent";
import { fill } from "../../../../lib/text";
import styles from "./ScanHeader.module.css";

// "digging deeper..." + target, with pause / stop and the turning logo while the scan runs.
//   control: "running" | "pausing" | "paused" | "resuming" (hooks/useScanStream)
// The pause button shows resume (▶) as soon as a pause is asked for, and waits while a resume is
// on its way. Pause needs the scan's id (canPause); stop works from the first moment, even while
// the server is still waking up.
export default function ScanHeader({ targetUrl, active, control = "running", canPause = true, stopping = false, onTogglePause, onStop }) {
    const { scan } = useContent();
    const held = control === "pausing" || control === "paused";
    const stateText = control === "running" ? null : scan.pauseState[control];

    return (
        <div className={styles.header}>
            <div>
                <h2 className={styles.title}>{scan.title}</h2>
                <p className={styles.target}>{fill(scan.targeting, { target: targetUrl })}</p>
                {active && stateText ? (
                    <p className={styles.state} role="status">
                        {stateText}
                    </p>
                ) : null}
            </div>

            {active ? (
                <div className={styles.controls}>
                    <button
                        type="button"
                        onClick={onTogglePause}
                        className={styles.control}
                        disabled={!canPause || control === "resuming"}
                        aria-pressed={held}
                        aria-label={held ? scan.controls.resume : scan.controls.pause}
                    >
                        <span className={styles.icon}>{held ? "▶" : "||"}</span>
                    </button>

                    <button
                        type="button"
                        onClick={onStop}
                        className={`${styles.control} ${styles.stop}`}
                        disabled={stopping}
                        aria-label={scan.controls.stop}
                    >
                        <span className={styles.square} />
                    </button>

                    <div className={styles.logoBox}>
                        <span className={styles.logo}>
                            <Spinner label={scan.controls.spinnerAlt} paused={control === "paused"} />
                        </span>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
