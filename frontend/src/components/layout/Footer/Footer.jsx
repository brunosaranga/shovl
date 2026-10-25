import LegalLinks from "../../sections/legal/LegalLinks/LegalLinks";
import { useContent } from "../../../hooks/useContent";
import styles from "./Footer.module.css";

// The line along the bottom of the ground (desktop). With `links`, the legal links follow it:
// Layout shows them on the landing only (phones get them under the launch card instead, since
// the footer is hidden there). The legal and pricing pages carry the row themselves.
export default function Footer({ links = false }) {
    const { common } = useContent();
    return (
        <footer className={styles.footer}>
            <span>{common.footer}</span>
            {links ? <LegalLinks variant="footer" /> : null}
        </footer>
    );
}
