import styles from "./Switch.module.css";

// An on/off switch: a square knob in a bordered track, neon when on, with "on" / "off"
// written next to it (colour alone never carries the meaning). role="switch", so screen
// readers announce it as a switch and its state.
export default function Switch({ checked, onChange, label, onText = "on", offText = "off", disabled = false, busy = false }) {
    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
            aria-label={label}
            aria-busy={busy || undefined}
            disabled={disabled || busy}
            className={styles.switch}
            onClick={() => onChange(!checked)}
        >
            <span className={styles.track} aria-hidden="true">
                <span className={styles.knob} />
            </span>
            <span className={styles.text} aria-hidden="true">
                {checked ? onText : offText}
            </span>
        </button>
    );
}
