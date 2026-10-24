import styles from "./BellModal.module.css";

// One collapsible row, built like the FAQ's: the title and an info line, and an arrow on the
// far right that turns down while the row is open. Native <details>, so it opens with a
// click, Enter or Space, and every row starts closed each time the bell opens.
export default function BellRow({ title, info, onOpen, children }) {
    return (
        <details
            className={styles.item}
            onToggle={(event) => event.currentTarget.open && onOpen?.()}
        >
            <summary className={styles.row}>
                <span className={styles.rowText}>
                    <span className={styles.rowTitle}>{title}</span>
                    <span className={styles.rowInfo}>{info}</span>
                </span>
                <span className={styles.arrow} aria-hidden="true">
                    →
                </span>
            </summary>
            <div className={styles.detail}>{children}</div>
        </details>
    );
}
