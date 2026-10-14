import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import userAvatar from "../../../assets/logos/UserAvatar.svg";
import { useSession } from "../../../context/SessionContext";
import { useContent } from "../../../hooks/useContent";
import { menuRoutes, canAccess } from "../../../routes";
import styles from "./Navbar.module.css";

// Avatar button. Nobody signed in → goes to /signin. Otherwise opens the menu:
//   pages from routes.jsx the visitor can open, then
//   guest:      "save your scans" (register) and "sign in" (both keep their scans)
//   registered: "log out"
// Guests get no "log out": dropping a guest token would lose their scans.
export default function AccountMenu() {
    const { nav } = useContent();
    const { status, signOut } = useSession();
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

    if (status === "anonymous") {
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
            </button>

            {open ? (
                <div className={styles.menu} role="menu">
                    {pages.map((route) => (
                        <Link key={route.path} to={route.path} role="menuitem" className={styles.item} onClick={close}>
                            {nav.items[route.menuKey]}
                        </Link>
                    ))}

                    {status === "guest" ? (
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
