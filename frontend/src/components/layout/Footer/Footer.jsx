import LegalLinks from "../../sections/legal/LegalLinks/LegalLinks";
import { useContent } from "../../../hooks/useContent";
import styles from "./Footer.module.css";

// The line along the bottom of the ground (desktop). With `links`, the legal links follow it.
// Layout leaves them out on pages whose content scrolls over the ground: that content sits on
// top of the footer and would catch the clicks. Those pages reach the links through the account
// menu, and the legal and pricing pages carry the row themselves.
export default function Footer({ links = false }) {
    const { common } = useContent();
    return (
        <footer className={styles.footer}>
            <span>{common.footer}</span>
            {links ? <LegalLinks variant="footer" /> : null}
        </footer>
    );
}
