import styles from "./ProgressBar.module.css";

// Stepped neo-brutalist progress bar. size: lg (scan page) | sm (inline)
export default function ProgressBar({ value = 0, size = "lg", label }) {
    const clamped = Math.max(0, Math.min(100, value));
    return (
        <div
            className={[styles.track, styles[size]].join(" ")}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={clamped}
            aria-label={label}
        >
            <div className={styles.fill} style={{ width: `${clamped}%` }} />
        </div>
    );
}
