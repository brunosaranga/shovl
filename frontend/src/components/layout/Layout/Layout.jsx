import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { NavSlotProvider } from "../../../context/NavSlotContext";
import { FaqProvider } from "../../../context/FaqContext";
import { NotificationsProvider } from "../../../context/NotificationsContext";
import Navbar from "../Navbar/Navbar";
import Ground from "../Ground/Ground";
import Footer from "../Footer/Footer";
import FaqButton from "../Faq/FaqButton";
import FaqModal from "../Faq/FaqModal";
import BellModal from "../Bell/BellModal";
import { useEntrance } from "../../../hooks/useEntrance";
import { useRouteAmbiance } from "../../../hooks/useSounds";
import { isContentOverGround } from "../../../routes";
import styles from "./Layout.module.css";

// The shell every page sits in: fixed navbar, the ground graphic, the footer, and a
// scrolling content area. Pages put things in the navbar's middle slot with <NavCenter>.
// It also switches the ambiance loop on or off as the page changes (routes.jsx says where).
// The FAQ lives here too: the "?" button on desktop, the account menu on mobile. So does the
// bell (registered accounts): its button in the navbar on desktop, the account menu on mobile.
// Pages marked `content: "over-ground"` in routes.jsx scroll over the ground; the others
// keep the ground in front of their content (the scan page) or layer their own pieces.
// On the first page of a visit, the ground comes in alone and the rest fades in after it
// (hooks/useEntrance.js).
export default function Layout() {
    const [navSlot, setNavSlot] = useState(null);
    const { pathname } = useLocation();
    const overGround = isContentOverGround(pathname);
    const shellRef = useEntrance();
    useRouteAmbiance();

    return (
        <FaqProvider>
            <NotificationsProvider>
                <NavSlotProvider value={navSlot}>
                    <div className={styles.shell} ref={shellRef}>
                        <Navbar slotRef={setNavSlot} />
                        <Ground />
                        <Footer links={pathname === "/"} />
                        <main id="main" className={styles.content} data-layer={overGround ? "over-ground" : undefined}>
                            <Outlet />
                        </main>
                        <FaqButton />
                    </div>
                    <FaqModal />
                    <BellModal />
                </NavSlotProvider>
            </NotificationsProvider>
        </FaqProvider>
    );
}
