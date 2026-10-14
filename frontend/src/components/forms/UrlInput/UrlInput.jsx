import { useContent } from "../../../hooks/useContent";
import styles from "./UrlInput.module.css";

// "URL: [ paste your API URL... ]". Enter submits.
// error: null | "empty" (shakes, asks for a URL) | "invalid" (red border)
export default function UrlInput({ value, onChange, onSubmit, error = null, inputRef }) {
    const { landing } = useContent();

    return (
        <div className={styles.container}>
            <label className={styles.label} htmlFor="scan-url">
                {landing.url.label}
            </label>
            <input
                id="scan-url"
                ref={inputRef}
                type="url"
                inputMode="url"
                autoCapitalize="off"
                autoComplete="off"
                spellCheck={false}
                value={value}
                onChange={(event) => onChange(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && onSubmit()}
                placeholder={error === "empty" ? landing.url.placeholderEmpty : landing.url.placeholder}
                aria-label={landing.url.ariaLabel}
                aria-invalid={Boolean(error)}
                className={error ? `${styles.input} ${styles.error}` : styles.input}
            />
        </div>
    );
}
