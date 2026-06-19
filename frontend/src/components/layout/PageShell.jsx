import GroundCanvas from "./GroundCanvas";
import Navbar from "./Navbar";
import AppFooter from "./Footer";

export default function PageShell({ title, children, isLanding = false, urlValue, onUrlChange, onSearchSubmit }) {
    return (
        <div style={{ 
            position: 'relative', 
            height: '100vh', 
            width: '100vw',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            background: '#fff'
        }}>
            {/* Forwarding the URL state and handlers to the Navbar */}
            <Navbar 
                variant="app" 
                title={title} 
                urlValue={urlValue}
                onUrlChange={onUrlChange}
                onSearchSubmit={onSearchSubmit}
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