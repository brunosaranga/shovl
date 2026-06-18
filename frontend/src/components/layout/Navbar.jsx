import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Navbar({ title, children }) {
    // const { user, logout } = useAuth()
    const { user } = useAuth()
    const navigate = useNavigate()

    return (
        <nav style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: '64px',
            padding: '0 40px',
            borderBottom: '1px solid var(--color-border)',
            position: 'relative',
            zIndex: 10,
            background: 'white',
        }}>
            <div
                onClick={() => navigate('/')}
                style={{ cursor: 'pointer', width: '40px' }}
            >
                {/* shovl hand icon */}
                <span style={{ fontSize: '24px' }}>🖕</span>
            </div>

            {title && (
                <h1 style={{
                    fontWeight: 800,
                    fontSize: '28px',
                    position: 'absolute',
                    left: '50%',
                    transform: 'translateX(-50%)',
                }}>
                    {title}
                </h1>
            )}

            {children}

            {user && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontWeight: 700 }}>[ {user.email }]</span>
                    <div
                        onClick={() => navigate('/settings')}
                        style={{
                            width: '40px', height: '40px',
                            borderRadius: '50%',
                            border: '2px solid var(--color-text)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            cursor: 'pointer',
                        }}
                    >
                        👤
                    </div>
                </div>
            )}
        </nav>
    )
}