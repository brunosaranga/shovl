import Spinner from "../../../ui/Spinner/Spinner";
import { useContent } from "../../../../hooks/useContent";
import { fill } from "../../../../lib/text";
import styles from "./ScanHeader.module.css";

// "digging deeper..." + target, with pause / stop and the turning logo while the scan runs.
export default function ScanHeader({ targetUrl, active, paused, onTogglePause, onStop }) {
    const { scan } = useContent();

    return (
        <div className={styles.header}>
            <div>
                <h2 className={styles.title}>{scan.title}</h2>
                <p className={styles.target}>{fill(scan.targeting, { target: targetUrl })}</p>
            </div>

            {active ? (
                <div className={styles.controls}>
                    <button
                        type="button"
                        onClick={onTogglePause}
                        className={styles.control}
                        aria-label={paused ? scan.controls.resume : scan.controls.pause}
                    >
                        <span className={styles.icon}>{paused ? "▶" : "||"}</span>
                    </button>

                    <button type="button" onClick={onStop} className={`${styles.control} ${styles.stop}`} aria-label={scan.controls.stop}>
                        <span className={styles.square} />
                    </button>

                    <div className={styles.logoBox}>
                        <span className={styles.logo}>
                            <Spinner label={scan.controls.spinnerAlt} paused={paused} />
                        </span>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
