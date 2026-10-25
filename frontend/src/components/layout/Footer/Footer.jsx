import LegalLinks from "../../sections/legal/LegalLinks/LegalLinks";
import { useContent } from "../../../hooks/useContent";
import styles from "./Footer.module.css";

// The line along the bottom of the ground. With `links`, the legal links follow it: Layout
// shows them on the landing only. Desktop shows the line and the links; phones show just the
// links, on the dunes right above the bottom navbar. The legal and pricing pages carry the row
// themselves.
export default function Footer({ links = false }) {
    const { common } = useContent();
    return (
        <footer className={styles.footer} data-links={links ? "" : undefined}>
            <span className={styles.line}>{common.footer}</span>
            {links ? <LegalLinks variant="footer" /> : null}
        </footer>
    );
}
