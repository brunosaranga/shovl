import { Navigate, useLocation } from "react-router-dom";
import { useSession } from "../../../context/SessionContext";
import { canAccess } from "../../../routes";

// Wraps every route (see routes.jsx). When the visitor can't open the page:
//   just logged out, or a guest session ended        → the start page
//   nobody signed in (or a registered session ended) → /signin, then back here
//   a guest on a registered-only page                → /signin, register tab, then back here
// `from` + `fromState` let the sign-in page return to exactly where the visitor was.
export default function AccessGate({ access, children }) {
    const { status, ended } = useSession();
    const location = useLocation();

    if (canAccess(access, status)) return children;

    if (status === "anonymous" && (ended?.reason === "logout" || ended?.wasGuest)) {
        return <Navigate to="/" replace />;
    }

    const back = { from: location.pathname, fromState: location.state ?? null };

    if (status === "anonymous") {
        return <Navigate to="/signin" replace state={{ ...back, notice: ended?.reason === "expired" ? "expired" : undefined }} />;
    }

    return <Navigate to="/signin" replace state={{ ...back, mode: "register", notice: "registerToContinue" }} />;
}
