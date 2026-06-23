import React from 'react'
import { useNavigate } from 'react-router-dom'
import shovlLogo from '../../assets/shovl-logo.svg'
import userAvatarIcon from '../../assets/UserAvatar.svg'

export default function Navbar({ 
    centerElement, // Highly flexible prop to inject text, inputs, or headers dynamically
    isAuthenticated = false, 
}) {
    const navigate = useNavigate()

    return (
        <nav className='navbar'>

            {/* Brand Logo Asset / Home Navigation */}
            <div
                className='shovl-logo-container' 
                onClick={() => navigate('/')}
                role="button"
                tabIndex={0}
                aria-label="shovl home"
                onKeyDown={(e) => e.key === 'Enter' && navigate('/')}
                onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.97)'}
                onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
                <img 
                    src={shovlLogo} 
                    alt="shovl logo"
                    className='shovl-logo' 
                    style={{ 
                        height: '40px', 
                        width: 'auto',
                        pointerEvents: 'none'
                    }} 
                />
            </div>

            {/* Decoupled Middle Slot */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {centerElement}
            </div>

            {/* Account Icon Layer */}
            <div
                className='acc-icon-container'
                onClick={() => {
                    if (isAuthenticated) {
                        navigate('/dashboard')
                    } else {
                        navigate('/signin')
                    }
                }}
                onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.95)'}
                onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
                <img 
                    src={userAvatarIcon} 
                    alt="account menu" 
                    style={{ width: '100%', height: '100%' }} 
                />
            </div>
        </nav>
    )
}