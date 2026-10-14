import { useContent } from "../../../../hooks/useContent";
import styles from "./AuthTabs.module.css";

// "sign in · register" switch above the form.
export default function AuthTabs({ mode, onChange }) {
    const { auth } = useContent();
    return (
        <div className={styles.tabs} role="tablist">
            {["signin", "register"].map((key) => (
                <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={mode === key}
                    className={mode === key ? `${styles.tab} ${styles.active}` : styles.tab}
                    onClick={() => onChange(key)}
                >
                    {auth.tabs[key]}
                </button>
            ))}
        </div>
    );
}
