import GroundCanvas from "./GroundCanvas";
import Navbar from "./Navbar";
import AppFooter from "./Footer";

export default function PageShell({ children, isLanding = false, centerElement }) {
    return (
        <div style={{ 
            position: 'relative', 
            height: '100vh', 
            width: '100vw',
            // overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            background: '#fff',
            boxSizing: 'border-box',
        }}>
            {/* Navbar dynamically receives the dynamic page title and custom center elements */}
            <Navbar 
                isAuthenticated={true} 
                centerElement={centerElement} 
            />
            
            <div style={{ 
                flexGrow: 1, 
                position: 'relative', 
                padding: isLanding ? '0' : '40px 80px',
                paddingBottom: isLanding ? '0' : '120px'
            }}>
                {children}
            </div>

            <GroundCanvas height={260} />
            <AppFooter />
        </div>
    )
}