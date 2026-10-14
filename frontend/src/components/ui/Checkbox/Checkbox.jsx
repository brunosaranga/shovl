import { useId } from "react";
import styles from "./Checkbox.module.css";

// Checkbox with a wrapping label (the consent ticks). `invalid` shakes it and turns the label red.
export default function Checkbox({ label, checked, onChange, invalid = false, className = "", inputRef }) {
    const id = useId();
    return (
        <div className={[styles.row, invalid ? `${styles.invalid} shake` : "", className].filter(Boolean).join(" ")}>
            <input
                id={id}
                ref={inputRef}
                type="checkbox"
                className={styles.box}
                checked={checked}
                aria-invalid={invalid}
                onChange={(event) => onChange(event.target.checked)}
            />
            <label htmlFor={id} className={styles.label}>
                {label}
            </label>
        </div>
    );
}
