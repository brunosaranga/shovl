import GroundCanvas from "./GroundCanvas";
import Navbar from "./Navbar";
import AppFooter from "./Footer";

// what is isLanding for?
export default function PageShell({ children, centerElement }) {
    return (
        <div className="pageshell">

            {/* Navbar dynamically receives the dynamic page title and custom center elements */}
            <Navbar 
                isAuthenticated={true} 
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