import { Navigate, useLocation } from "react-router-dom";
import { useSession } from "../../../context/SessionContext";
import { canAccess } from "../../../routes";

// Wraps every route (see routes.jsx). When the visitor can't open the page:
//   an account whose email isn't confirmed yet       → /confirm-email, then back here
//   a confirmed account on the code screen           → where it was going, else the dashboard
//   just logged out, or a guest session ended        → the start page
//   nobody signed in (or a registered session ended) → /signin, then back here
//   a guest on a registered-only page                → /signin, register tab, then back here
// `from` + `fromState` let the sign-in page (and the code screen) return to exactly where the
// visitor was.
export default function AccessGate({ access, children }) {
    const { status, ended } = useSession();
    const location = useLocation();

    if (canAccess(access, status)) return children;

    const back = { from: location.pathname, fromState: location.state ?? null };

    if (status === "unconfirmed") {
        return <Navigate to="/confirm-email" replace state={back} />;
    }

    if (access === "unconfirmed" && status === "registered") {
        const state = location.state || {};
        return <Navigate to={state.from || "/dashboard"} replace state={state.fromState ?? undefined} />;
    }

    if (status === "anonymous" && (ended?.reason === "logout" || ended?.wasGuest)) {
        return <Navigate to="/" replace />;
    }

    if (status === "anonymous") {
        return <Navigate to="/signin" replace state={{ ...back, notice: ended?.reason === "expired" ? "expired" : undefined }} />;
    }

    return <Navigate to="/signin" replace state={{ ...back, mode: "register", notice: "registerToContinue" }} />;
}
