import { useId } from "react";
import styles from "./TextField.module.css";

// Labelled input with an optional hint and a list of errors from the server.
export default function TextField({ label, hint, errors = [], className = "", ...inputProps }) {
    const id = useId();
    const hintId = hint ? `${id}-hint` : undefined;
    const errorId = errors.length ? `${id}-errors` : undefined;

    return (
        <div className={[styles.field, className].filter(Boolean).join(" ")}>
            <label className={styles.label} htmlFor={id}>
                {label}
            </label>
            <input
                id={id}
                className={[styles.input, errors.length ? styles.invalid : ""].filter(Boolean).join(" ")}
                aria-invalid={errors.length > 0}
                aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
                {...inputProps}
            />
            {hint ? (
                <p id={hintId} className={styles.hint}>
                    {hint}
                </p>
            ) : null}
            {errors.length ? (
                <ul id={errorId} className={styles.errors}>
                    {errors.map((message) => (
                        <li key={message}>{message}</li>
                    ))}
                </ul>
            ) : null}
        </div>
    );
}
