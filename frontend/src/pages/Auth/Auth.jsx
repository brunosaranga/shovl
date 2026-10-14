import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import Logo from "../../components/ui/Logo/Logo";
import AuthIntro from "../../components/sections/auth/AuthIntro/AuthIntro";
import AuthTabs from "../../components/sections/auth/AuthTabs/AuthTabs";
import AuthForm from "../../components/forms/AuthForm/AuthForm";
import { useSession } from "../../context/SessionContext";
import { useContent } from "../../hooks/useContent";
import { isPracticeTarget } from "../../lib/targets";
import styles from "./Auth.module.css";

// Where to go once signed in:
//   back to the page that sent us here, else
//   the scan that was waiting (practice → straight to scanning, own domain → verify), else
//   the dashboard.
function destination(state) {
    if (state?.from) return { to: state.from, state: state.fromState ?? undefined };
    const pending = state?.pendingScan;
    if (pending?.url) return { to: isPracticeTarget(pending.url) ? "/scan/running" : "/verify", state: pending };
    return { to: "/dashboard" };
}

export default function Auth() {
    const { auth } = useContent();
    const { status } = useSession();
    const location = useLocation();
    const state = location.state || {};
    const [mode, setMode] = useState(state.mode === "register" ? "register" : "signin");

    // Registered (already, or just now after the form succeeded): move on.
    if (status === "registered") {
        const next = destination(state);
        return <Navigate to={next.to} state={next.state} replace />;
    }

    const notice = state.notice ? auth.notices[state.notice] : null;

    return (
        <>
            <PageMeta title={auth.meta[mode]} />

            <div className={styles.container}>
                <AuthIntro />

                <div className={styles.right}>
                    <div className={styles.header}>
                        <Logo variant="lockup" as="p" />
                        <p className={styles.mobileTagline}>{auth.intro.title}</p>
                        <AuthTabs mode={mode} onChange={setMode} />
                    </div>

                    <AuthForm key={mode} mode={mode} notice={notice} />
                </div>
            </div>
        </>
    );
}
