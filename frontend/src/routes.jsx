import Layout from "./components/layout/Layout/Layout";
import AccessGate from "./components/layout/AccessGate/AccessGate";
import Landing from "./pages/Landing/Landing";
import Auth from "./pages/Auth/Auth";
import Verify from "./pages/Verify/Verify";
import ScanRunning from "./pages/ScanRunning/ScanRunning";
import Report from "./pages/Report/Report";
import Dashboard from "./pages/Dashboard/Dashboard";
import Settings from "./pages/Settings/Settings";
import NotFound from "./pages/NotFound/NotFound";

// Single source of truth: the router AND the account menu read this list.
//
// access:
//   public      → anyone
//   session     → a guest or a registered account (guests can scan practice targets)
//   registered  → registered accounts only (guests are sent to register)
// menuKey: shows the page in the account menu; the label lives in content/en/nav.js.
export const pageRoutes = [
    { path: "/", element: <Landing />, access: "public" },
    { path: "/signin", element: <Auth />, access: "public" },
    { path: "/verify", element: <Verify />, access: "registered" },
    { path: "/scan/running", element: <ScanRunning />, access: "session" },
    { path: "/scan/:scanId/report", element: <Report />, access: "session" },
    { path: "/dashboard", element: <Dashboard />, access: "session", menuKey: "dashboard" },
    { path: "/settings", element: <Settings />, access: "registered", menuKey: "settings" },
];

export const menuRoutes = pageRoutes.filter((route) => route.menuKey);

const ALLOWED = {
    public: ["anonymous", "guest", "registered"],
    session: ["guest", "registered"],
    registered: ["registered"],
};

/** Can someone with this session status open a route with this access level? */
export function canAccess(access, status) {
    return (ALLOWED[access] || ALLOWED.registered).includes(status);
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
