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
        <nav style={{
            display: 'flex', 
            alignItems: 'center',
            justifyContent: 'space-between',
            height: '64px', 
            padding: '0 40px',
            position: 'relative', 
            zIndex: 10, 
            background: 'white',
            width: '100%',
        }}>

            {/* Brand Logo Asset / Home Navigation */}
            <div 
                onClick={() => navigate('/')}
                role="button"
                tabIndex={0}
                aria-label="shovl home"
                onKeyDown={(e) => e.key === 'Enter' && navigate('/')}
                style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '40px',
                    cursor: 'pointer',
                    userSelect: 'none',
                    outline: 'none',
                    transition: 'transform 0.1s ease'
                }}
                onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.97)'}
                onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
                <img 
                    src={shovlLogo} 
                    alt="shovl logo" 
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
                onClick={() => {
                    if (isAuthenticated) {
                        navigate('/dashboard')
                    } else {
                        navigate('/signin')
                    }
                }}
                style={{
                    width: '40px', 
                    height: '40px', 
                    borderRadius: '50%',
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    cursor: 'pointer',
                    overflow: 'hidden',
                    background: '#fff',
                    transition: 'transform 0.1s ease',
                }}
                onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.95)'}
                onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
                <img 
                    src={userAvatarIcon} 
                    alt="account menu" 
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                />
            </div>
        </nav>
    )
}