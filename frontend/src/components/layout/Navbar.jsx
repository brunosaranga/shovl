import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import shovlLogo from '../../assets/shovl-logo.svg'
import userAvatarIcon from '../../assets/UserAvatar.svg'
import { useAuth } from '../../hooks/useAuth'

export default function Navbar({
    centerElement, // Highly flexible prop to inject text, inputs, or headers dynamically
    isAuthenticated = false,
}) {
    const navigate = useNavigate()
    const { logout } = useAuth()
    const [menuOpen, setMenuOpen] = useState(false)
    const menuRef = useRef(null)

    // Close the account menu on any outside click.
    useEffect(() => {
        if (!menuOpen) return
        const onClick = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false)
        }
        document.addEventListener('mousedown', onClick)
        return () => document.removeEventListener('mousedown', onClick)
    }, [menuOpen])

    const handleAvatarClick = () => {
        if (isAuthenticated) {
            setMenuOpen((o) => !o)
        } else {
            navigate('/signin')
        }
    }

    const handleLogout = () => {
        logout()
        setMenuOpen(false)
        navigate('/')
    }

    const go = (path) => {
        setMenuOpen(false)
        navigate(path)
    }

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
                    style={{ height: '40px', width: 'auto', pointerEvents: 'none' }}
                />
            </div>

            {/* Decoupled Middle Slot */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {centerElement}
            </div>

            {/* Account Icon + dropdown */}
            <div className='acc-menu-wrapper' style={{ position: 'relative' }} ref={menuRef}>
                <div
                    className='acc-icon-container'
                    onClick={handleAvatarClick}
                    role="button"
                    tabIndex={0}
                    aria-label="account menu"
                    aria-haspopup="menu"
                    aria-expanded={menuOpen}
                    onKeyDown={(e) => e.key === 'Enter' && handleAvatarClick()}
                    onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.95)'}
                    onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
                >
                    <img src={userAvatarIcon} alt="account menu" style={{ width: '100%', height: '100%' }} />
                </div>

                {isAuthenticated && menuOpen && (
                    <div
                        className='acc-dropdown'
                        role="menu"
                        style={{
                            position: 'absolute',
                            right: 0,
                            top: 'calc(100% + 8px)',
                            background: 'var(--color-bg, #fff)',
                            border: '2px solid var(--color-text, #111)',
                            boxShadow: '4px 4px 0 var(--color-text, #111)',
                            minWidth: '160px',
                            zIndex: 50,
                        }}
                    >
                        <button className='acc-dropdown-item' role="menuitem" onClick={() => go('/dashboard')}>
                            dashboard
                        </button>
                        <button className='acc-dropdown-item' role="menuitem" onClick={() => go('/settings')}>
                            settings
                        </button>
                        <button className='acc-dropdown-item is-danger' role="menuitem" onClick={handleLogout}>
                            log out
                        </button>
                    </div>
                )}
            </div>
        </nav>
    )
}