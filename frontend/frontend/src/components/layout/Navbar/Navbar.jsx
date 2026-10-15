import { Link } from "react-router-dom";
import Logo from "../../ui/Logo/Logo";
import SoundToggle from "../../ui/SoundToggle/SoundToggle";
import ThemeToggle from "../../ui/ThemeToggle/ThemeToggle";
import AccountMenu from "./AccountMenu";
import { useContent } from "../../../hooks/useContent";
import styles from "./Navbar.module.css";

// Logo (home) · middle slot (filled by the page) · sound + theme toggles + account menu.
// Desktop: fixed at the top. Mobile: a dark bar fixed at the bottom.
export default function Navbar({ slotRef }) {
    const { common } = useContent();

    return (
        <nav className={styles.navbar}>
            <Link to="/" className={styles.home} aria-label={common.homeLabel}>
                <Logo variant="mark" />
            </Link>

            <div className={styles.center} ref={slotRef} />

            <div className={styles.right}>
                <SoundToggle className={styles.barToggle} />
                <ThemeToggle className={styles.barToggle} />
                <AccountMenu />
            </div>
        </nav>
    );
}
