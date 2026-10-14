import shovlLogo from "../../../assets/logos/shovl-logo.svg";
import { useContent } from "../../../hooks/useContent";
import styles from "./Logo.module.css";

// variant:
//   mark    → just the hand-and-shovel icon (navbar)
//   lockup  → "shovl" wordmark + icon (auth page, mobile landing header)
export default function Logo({ variant = "mark", as: Heading = "h1" }) {
    const { common } = useContent();

    if (variant === "lockup") {
        return (
            <div className={styles.lockup}>
                <Heading className={styles.wordmark}>{common.brand}</Heading>
                <img className={styles.lockupMark} src={shovlLogo} alt="" />
            </div>
        );
    }

    return <img className={styles.mark} src={shovlLogo} alt={common.logoAlt} />;
}
