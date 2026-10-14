import shovlLogo from "../../../assets/logos/shovl-logo.svg";
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
