import { Link } from "react-router-dom";
import Logo from "../../ui/Logo/Logo";
import SoundToggle from "../../ui/SoundToggle/SoundToggle";
import ThemeToggle from "../../ui/ThemeToggle/ThemeToggle";
import AccountMenu from "./AccountMenu";
import BellButton from "../Bell/BellButton";
import { useContent } from "../../../hooks/useContent";
import styles from "./Navbar.module.css";

// Logo (home) · middle slot (filled by the page) · bell + sound + theme toggles + account menu.
// Desktop: fixed at the top. Mobile: a dark bar fixed at the bottom (the bell moves into the
// account menu there).
export default function Navbar({ slotRef }) {
    const { common } = useContent();

    return (
        <nav className={styles.navbar}>
            <Link to="/" className={styles.home} aria-label={common.homeLabel}>
                <Logo variant="mark" inverseOnMobile />
            </Link>

            <div className={styles.center} ref={slotRef} />

            <div className={styles.right}>
                <BellButton />
                <SoundToggle className={styles.barToggle} />
                <ThemeToggle className={styles.barToggle} />
                <AccountMenu />
            </div>
        </nav>
    );
}
