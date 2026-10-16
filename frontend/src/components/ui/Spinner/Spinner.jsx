// Same built-in copy as ui/Logo, so the spinner never waits for a download either.
import shovlLogo from "../../../assets/logos/shovl-logo.svg?inline";
import styles from "./Spinner.module.css";

// The logo turning in eight steps. Stops in place when `paused`.
export default function Spinner({ label, paused = false, className = "" }) {
    return (
        <img
            src={shovlLogo}
            alt={label || ""}
            className={[styles.spinner, paused ? styles.paused : "", className].filter(Boolean).join(" ")}
        />
    );
}
