import GroundCanvas from "./GroundCanvas";
import Navbar from "./Navbar";
import AppFooter from "./Footer";
import { useAuth } from "../../hooks/useAuth";

export default function PageShell({ children, centerElement }) {
    const { accessToken } = useAuth()
    const isAuthenticated = Boolean(accessToken || localStorage.getItem('access_token'))

    return (
        <div className="pageshell">

            {/* Navbar dynamically receives the dynamic page title and custom center elements */}
            <Navbar
                isAuthenticated={isAuthenticated}
                centerElement={centerElement}
            />

            <div className="pageshell-content-container">
                {children}
                <GroundCanvas />
                <AppFooter />
            </div>
        </div>
    )
}