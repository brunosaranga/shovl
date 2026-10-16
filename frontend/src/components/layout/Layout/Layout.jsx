import { useState } from "react";
import { Outlet } from "react-router-dom";
import { NavSlotProvider } from "../../../context/NavSlotContext";
import { FaqProvider } from "../../../context/FaqContext";
import Navbar from "../Navbar/Navbar";
import Ground from "../Ground/Ground";
import Footer from "../Footer/Footer";
import FaqButton from "../Faq/FaqButton";
import FaqModal from "../Faq/FaqModal";
import { useRouteAmbiance } from "../../../hooks/useSounds";
import styles from "./Layout.module.css";

// The shell every page sits in: fixed navbar, the ground graphic, the footer, and a
// scrolling content area. Pages put things in the navbar's middle slot with <NavCenter>.
// It also switches the ambiance loop on or off as the page changes (routes.jsx says where).
// The FAQ lives here too: the "?" button on desktop, the account menu on mobile.
export default function Layout() {
    const [navSlot, setNavSlot] = useState(null);
    useRouteAmbiance();

    return (
        <FaqProvider>
            <NavSlotProvider value={navSlot}>
                <div className={styles.shell}>
                    <Navbar slotRef={setNavSlot} />
                    <Ground />
                    <Footer />
                    <main id="main" className={styles.content}>
                        <Outlet />
                    </main>
                    <FaqButton />
                </div>
                <FaqModal />
            </NavSlotProvider>
        </FaqProvider>
    );
}
