import { useState } from "react";
import styles from "./CopyField.module.css";

// Dark panel showing a value, with a copy-to-clipboard button.
export default function CopyField({ value, copyLabel, copiedLabel }) {
    const [copied, setCopied] = useState(false);

    const copy = async () => {
        try {
            await navigator.clipboard.writeText(value);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // clipboard blocked: the value is still selectable on screen
        }
    };

    return (
        <div className={styles.field}>
            <code className={styles.value}>{value}</code>
            <button type="button" onClick={copy} className={copied ? `${styles.button} ${styles.copied}` : styles.button}>
                {copied ? copiedLabel : copyLabel}
            </button>
        </div>
    );
}
