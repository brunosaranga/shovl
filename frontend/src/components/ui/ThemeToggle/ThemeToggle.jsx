import { useTheme } from "../../../context/ThemeContext";
import { useContent } from "../../../hooks/useContent";
import styles from "./ThemeToggle.module.css";

// Square button in the navbar: a moon in light mode, a sun in dark mode.
export default function ThemeToggle({ className = "" }) {
    const { theme, toggleTheme } = useTheme();
    const { common } = useContent();
    const dark = theme === "dark";

    return (
        <button
            type="button"
            className={[styles.toggle, className].filter(Boolean).join(" ")}
            onClick={toggleTheme}
            aria-label={dark ? common.theme.toLight : common.theme.toDark}
            aria-pressed={dark}
            title={dark ? common.theme.toLight : common.theme.toDark}
        >
            {dark ? (
                <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.icon}>
                    <circle cx="12" cy="12" r="4.5" fill="currentColor" />
                    <g stroke="currentColor" strokeWidth="2.2" strokeLinecap="square">
                        <path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M4.6 19.4l2.1-2.1M17.3 6.7l2.1-2.1" />
                    </g>
                </svg>
            ) : (
                <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.icon}>
                    <path fill="currentColor" d="M20.5 14.6A8.5 8.5 0 0 1 9.4 3.5a8.5 8.5 0 1 0 11.1 11.1Z" />
                </svg>
            )}
        </button>
    );
}
