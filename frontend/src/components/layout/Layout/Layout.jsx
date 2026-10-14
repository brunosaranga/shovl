import { useState } from "react";
import { Outlet } from "react-router-dom";
import { NavSlotProvider } from "../../../context/NavSlotContext";
import Navbar from "../Navbar/Navbar";
import Ground from "../Ground/Ground";
import Footer from "../Footer/Footer";
import styles from "./Layout.module.css";

// The shell every page sits in: fixed navbar, the ground graphic, the footer, and a
// scrolling content area. Pages put things in the navbar's middle slot with <NavCenter>.
export default function Layout() {
    const [navSlot, setNavSlot] = useState(null);

    return (
        <NavSlotProvider value={navSlot}>
            <div className={styles.shell}>
                <Navbar slotRef={setNavSlot} />
                <Ground />
                <Footer />
                <main id="main" className={styles.content}>
                    <Outlet />
                </main>
            </div>
        </NavSlotProvider>
    );
}
