// The same built-in logo as ui/Logo (ui/LogoImage), so the spinner never waits for a download either.
import LogoImage from "../LogoImage/LogoImage";
import styles from "./Spinner.module.css";

// The logo turning in eight steps. Stops in place when `paused`.
export default function Spinner({ label, paused = false, className = "" }) {
    return (
        <LogoImage
            alt={label || ""}
            className={[styles.spinner, paused ? styles.paused : "", className].filter(Boolean).join(" ")}
        />
    );
}
