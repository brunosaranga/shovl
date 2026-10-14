import Card from "../../../ui/Card/Card";
import styles from "./SettingsSection.module.css";

// A settings card: dark header bar, then rows.
export default function SettingsSection({ title, children }) {
    return (
        <Card as="section" border={3} shadow={6}>
            <h2 className={styles.header}>{title}</h2>
            <div className={styles.body}>{children}</div>
        </Card>
    );
}

// label · value · optional action, on a three-column grid.
export function SettingsRow({ label, value, action }) {
    return (
        <div className={styles.row}>
            <span className={styles.label}>{label}</span>
            <span className={styles.value}>{value}</span>
            <span>{action}</span>
        </div>
    );
}
