import styles from "./Alert.module.css";

// Bordered panel for something the user needs to read: a failure, a refusal, a notice.
//   tone: danger (red, the old "verification failed" panel) | info (black) | accent (neon edge)
export default function Alert({ tone = "danger", title, children, actions, role, className = "" }) {
    return (
        <div className={[styles.alert, styles[tone], className].filter(Boolean).join(" ")} role={role}>
            {title ? <span className={styles.title}>{title}</span> : null}
            {children ? <div className={styles.body}>{children}</div> : null}
            {actions ? <div className={styles.actions}>{actions}</div> : null}
        </div>
    );
}
