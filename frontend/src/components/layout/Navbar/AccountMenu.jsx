import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import userAvatar from "../../../assets/logos/UserAvatar.svg";
import { useSession } from "../../../context/SessionContext";
import { useFaq } from "../../../context/FaqContext";
import { useNotifications } from "../../../context/NotificationsContext";
import { useContent } from "../../../hooks/useContent";
import { MOBILE_QUERY, useMediaQuery } from "../../../hooks/useMediaQuery";
import { menuRoutes, canAccess } from "../../../routes";
import styles from "./Navbar.module.css";

// Avatar button. Opens the menu:
//   pages from routes.jsx the visitor can open, then
//   mobile:     "notifications" for registered accounts (desktop has the bell in the
//               navbar), with a dot on the avatar while there's something new, then
//               "faq" (desktop has the "?" button in the corner instead)
//   nobody:     "sign in"
//   guest:      "save your scans" (register) and "sign in" (both keep their scans)
//   registered: "log out"; so does an unconfirmed account, which sees no pages here (they all
//               lead to the code screen until it's confirmed) and no bell
// Nobody signed in on desktop: no menu, the avatar goes straight to /signin.
// On mobile they get the menu too, or the FAQ would be out of reach.
// Guests get no "log out": dropping a guest token would lose their scans.
export default function AccountMenu() {
    const { nav, notifications } = useContent();
    const { status, signOut } = useSession();
    const { openFaq } = useFaq();
    const bell = useNotifications();
    const isMobile = useMediaQuery(MOBILE_QUERY);
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const wrapperRef = useRef(null);

    useEffect(() => {
        if (!open) return undefined;
        const onPointer = (event) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) setOpen(false);
        };
        const onKey = (event) => event.key === "Escape" && setOpen(false);
        document.addEventListener("mousedown", onPointer);
        document.addEventListener("keydown", onKey);
        return () => {
            document.removeEventListener("mousedown", onPointer);
            document.removeEventListener("keydown", onKey);
        };
    }, [open]);

    const avatar = <img src={userAvatar} alt="" className={styles.avatarImage} />;

    if (status === "anonymous" && !isMobile) {
        return (
            <Link to="/signin" className={styles.avatar} aria-label={nav.guestSignIn}>
                {avatar}
            </Link>
        );
    }

    const close = () => setOpen(false);
    const pages = menuRoutes.filter((route) => canAccess(route.access, status));

    return (
        <div className={styles.menuWrapper} ref={wrapperRef}>
            <button
                type="button"
                className={styles.avatar}
                aria-label={nav.accountMenu}
                aria-haspopup="menu"
                aria-expanded={open}
                onClick={() => setOpen((value) => !value)}
            >
                {avatar}
                {isMobile && bell.enabled && bell.badge ? <span className={styles.dot} aria-hidden="true" /> : null}
            </button>

            {open ? (
                <div className={styles.menu} role="menu">
                    {pages.map((route) => (
                        <Link key={route.path} to={route.path} role="menuitem" className={styles.item} onClick={close}>
                            {nav.items[route.menuKey]}
                        </Link>
                    ))}

                    {isMobile && bell.enabled ? (
                        <button
                            type="button"
                            role="menuitem"
                            aria-haspopup="dialog"
                            className={styles.item}
                            onClick={() => {
                                close();
                                bell.openBell();
                            }}
                        >
                            {notifications.menuItem}
                            {bell.badge ? <span className={styles.itemCount}>{bell.badge > 9 ? "9+" : bell.badge}</span> : null}
                        </button>
                    ) : null}

                    {isMobile ? (
                        <button
                            type="button"
                            role="menuitem"
                            aria-haspopup="dialog"
                            className={styles.item}
                            onClick={() => {
                                close();
                                openFaq();
                            }}
                        >
                            {nav.faq}
                        </button>
                    ) : null}

                    {status === "anonymous" ? (
                        <Link to="/signin" state={{ mode: "signin" }} role="menuitem" className={styles.item} onClick={close}>
                            {nav.guestSignIn}
                        </Link>
                    ) : status === "guest" ? (
                        <>
                            <Link
                                to="/signin"
                                state={{ mode: "register" }}
                                role="menuitem"
                                className={styles.item}
                                onClick={close}
                            >
                                {nav.guestRegister}
                            </Link>
                            <Link to="/signin" state={{ mode: "signin" }} role="menuitem" className={styles.item} onClick={close}>
                                {nav.guestSignIn}
                            </Link>
                        </>
                    ) : (
                        <button
                            type="button"
                            role="menuitem"
                            className={`${styles.item} ${styles.danger}`}
                            onClick={() => {
                                close();
                                signOut();
                                navigate("/");
                            }}
                        >
                            {nav.logout}
                        </button>
                    )}
                </div>
            ) : null}
        </div>
    );
}
