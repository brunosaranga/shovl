import GroundCanvas from "./GroundCanvas";
import Navbar from "./Navbar";
import AppFooter from "./Footer";

export default function PageShell({ title, children, isLanding = false }) {
    return (
        <div style={{ 
            position: 'relative', 
            height: '100vh', // Locks the app to the viewport
            width: '100vw',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            background: '#fff'
        }}>
            <Navbar variant="app" title={title} />
            
            {/* Main Content Wrapper */}
            <div style={{ 
                flexGrow: 1, // Forces this div to stretch and fill the remaining height
                position: 'relative', 
                padding: isLanding ? '0' : '40px 80px',
                paddingBottom: isLanding ? '0' : '120px' // Drops the heavy padding for the landing
            }}>
                {children}
            </div>

            <GroundCanvas height={260} />
            <AppFooter />
        </div>
    )
}