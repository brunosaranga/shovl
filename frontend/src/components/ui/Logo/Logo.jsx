// Built into the page bundle (?inline) rather than downloaded separately: the logo is on every
// page, and as its own file it left an empty gap (or the alt text) until the file arrived.
import shovllLogo from "../../../assets/logos/shovl-logo.svg?inline";
import { useContent } from "../../../hooks/useContent";
import styles from "./Logo.module.css";

// variant:
//   mark    → just the hand-and-shovel icon (navbar)
//   lockup  → "shovll" wordmark + icon (auth page, mobile landing header)
export default function Logo({ variant = "mark", as: Heading = "h1" }) {
    const { common } = useContent();

    if (variant === "lockup") {
        return (
            <div className={styles.lockup}>
                <Heading className={styles.wordmark}>{common.brand}</Heading>
                <img className={styles.lockupMark} src={shovllLogo} alt="" width="41" height="41" />
            </div>
        );
    }

    return <img className={styles.mark} src={shovllLogo} alt={common.logoAlt} width="40" height="40" />;
}
