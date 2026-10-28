import { matchPath } from "react-router-dom";
import Layout from "./components/layout/Layout/Layout";
import AccessGate from "./components/layout/AccessGate/AccessGate";
import Landing from "./pages/Landing/Landing";
import Auth from "./pages/Auth/Auth";
import Verify from "./pages/Verify/Verify";
import ConfirmEmail from "./pages/ConfirmEmail/ConfirmEmail";
import EmailOff from "./pages/EmailOff/EmailOff";
import ResetPassword from "./pages/ResetPassword/ResetPassword";
import ScanRunning from "./pages/ScanRunning/ScanRunning";
import Report from "./pages/Report/Report";
import Dashboard from "./pages/Dashboard/Dashboard";
import Settings from "./pages/Settings/Settings";
import NotFound from "./pages/NotFound/NotFound";
import Pricing from "./pages/Pricing/Pricing";
import Legal from "./pages/Legal/Legal";

// Single source of truth: the router AND the account menu read this list.
//
// access:
//   public      → anyone
//   session     → a guest or a registered account (guests can scan practice targets)
//   registered  → registered accounts only (guests are sent to register)
//   unconfirmed → only an account whose email isn't confirmed yet: the code screen. Such an
//                 account is sent there from every page that isn't public (AccessGate).
// menuKey: shows the page in the account menu; the label lives in content/en/nav.js.
// ambiance: false keeps the ambiance loop off on that page (lib/sound.js); every other
//   page, the 404 included, plays it.
// ground: "still" brings the walking ground to a halt on that page (layout/Ground): we stop
//   to dig while a scan runs, and stay put if it fails. Leaving walks on from the same spot.
// content: "over-ground" lets the page's content scroll over the ground, so nothing you need
//   to read or click hides behind it. Without it the ground covers the bottom of the page:
//   on purpose on the scan page (we're digging into it); the landing and sign-in pages
//   layer their own pieces (layout/Layout).
export const pageRoutes = [
    { path: "/", element: <Landing />, access: "public" },
    { path: "/signin", element: <Auth />, access: "public" },
    { path: "/confirm-email", element: <ConfirmEmail />, access: "unconfirmed", content: "over-ground" },
    // The "turn these emails off" link in murindzi's emails: works signed out, from any browser.
    { path: "/email-off", element: <EmailOff />, access: "public", content: "over-ground" },
    // "forgot your password?" on the sign-in tab: works signed out.
    { path: "/reset-password", element: <ResetPassword />, access: "public", content: "over-ground" },
    { path: "/verify", element: <Verify />, access: "registered", ambiance: false, content: "over-ground" },
    { path: "/scan/running", element: <ScanRunning />, access: "session", ambiance: false, ground: "still" },
    { path: "/scan/:scanId/report", element: <Report />, access: "session", content: "over-ground" },
    { path: "/dashboard", element: <Dashboard />, access: "session", menuKey: "dashboard", content: "over-ground" },
    { path: "/settings", element: <Settings />, access: "registered", menuKey: "settings", content: "over-ground" },
    // Linked from the footer, the account menu and the consent ticks (sections/legal/LegalLinks).
    { path: "/pricing", element: <Pricing />, access: "public", content: "over-ground" },
    { path: "/terms", element: <Legal doc="terms" />, access: "public", content: "over-ground" },
    { path: "/privacy", element: <Legal doc="privacy" />, access: "public", content: "over-ground" },
    { path: "/refunds", element: <Legal doc="refunds" />, access: "public", content: "over-ground" },
];

export const menuRoutes = pageRoutes.filter((route) => route.menuKey);

const ALLOWED = {
    public: ["anonymous", "guest", "unconfirmed", "registered"],
    session: ["guest", "registered"],
    registered: ["registered"],
    unconfirmed: ["unconfirmed"],
};

/** Can someone with this session status open a route with this access level? */
export function canAccess(access, status) {
    return (ALLOWED[access] || ALLOWED.registered).includes(status);
}

/** Does the page at this path play the ambiance loop? */
export function hasAmbiance(pathname) {
    return !pageRoutes.some((route) => route.ambiance === false && matchPath(route.path, pathname));
}

/** Does the ground stand still on the page at this path? */
export function isGroundStill(pathname) {
    return pageRoutes.some((route) => route.ground === "still" && matchPath(route.path, pathname));
}

/** Does the page at this path scroll its content over the ground (instead of under it)? */
export function isContentOverGround(pathname) {
    return pageRoutes.some((route) => route.content === "over-ground" && matchPath(route.path, pathname));
}

export const routerConfig = [
    {
        path: "/",
        element: <Layout />,
        children: [
            ...pageRoutes.map(({ path, element, access }) => {
                const gated = <AccessGate access={access}>{element}</AccessGate>;
                return path === "/" ? { index: true, element: gated } : { path: path.slice(1), element: gated };
            }),
            { path: "*", element: <NotFound /> },
        ],
    },
];
