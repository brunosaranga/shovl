import { authAPI } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import shovlLogo from '../assets/shovl-logo.svg' // Assuming this has the hand included, or import hand separately
// import PageTitle from '../components/common/PageTitle'

export default function Auth() {
    const navigate = useNavigate()
    const { login } = useAuth()

    // SPA Toggle State: 'signin' | 'register'
    const [view, setView] = useState('signin') 
    
    // Form States
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [consent, setConsent] = useState(false)
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (view === 'register' && !consent) return

        setError(null)
        setLoading(true)

        try {
            if (view === 'signin') {
            const res = await authAPI.login({ email, password })
            const token = res.data.access
            const meRes = await authAPI.me(token)
            login({ access: token }, meRes.data)
        } else {
            await authAPI.register({ email, password, tos_agreed: true })
            const res = await authAPI.login({ email, password })
            const token = res.data.access
            const meRes = await authAPI.me(token)
            login({ access: token }, meRes.data)
        }
            navigate('/dashboard')
        } catch (err) {
            setError(
                err.response?.data?.detail ||
                err.response?.data?.email?.[0] ||
                'something went wrong. try again.'
            )
        } finally {
            setLoading(false)
        }
    }

    return (
        <PageShell title={view === 'signin' ? 'sign in' : 'register'}>
            <div style={{
                maxWidth: '1000px',
                margin: '0 auto',
                paddingTop: '60px',
                display: 'flex',
                gap: '80px',
                alignItems: 'center',
                minHeight: '50vh',
                zIndex: 21,

            }}>
                
                {/* Left Column: Marketing & Imagery */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '30px' }}>
                    <h1 style={{
                        fontFamily: 'var(--font-display)',
                        fontSize: '32px',
                        fontWeight: 900,
                        lineHeight: 1.1,
                        color: 'var(--color-text)',
                        margin: 0,
                    }}>
                        Securing your APIs from commit to production.
                    </h1>
                    
                    {/* Placeholder for your Security Guard Incident Report graphic */}
                    <div style={{
                        width: '100%',
                        height: '240px',
                        background: '#f8f8f8',
                        border: '2px solid var(--color-text)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '4px 4px 0px var(--color-text)'
                    }}>
                        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-muted)' }}>
                            [ incident-report-asset.svg ]
                        </span>
                    </div>
                </div>



                {/* Right Column: Auth Card */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    
                    {/* Header: Logo & Tabs */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
                        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: '16px', marginBottom: '24px' }}>
                            <h1 style={{
                                fontFamily: 'var(--font-display)',
                                fontSize: '50px',
                                fontWeight: 400,
                                lineHeight: 1,
                                letterSpacing: '-6px',
                                userSelect: 'none',
                                color: 'var(--color-text)'
                            }}>
                                shovl
                            </h1>
                            <img src={shovlLogo} alt="shovl" style={{ height: '48px' }} />
                        </div>
                        
                        <div style={{ 
                            display: 'flex', 
                            gap: '24px', 
                            fontFamily: 'var(--font-display)', 
                            fontSize: '24px',
                            fontWeight: 900 
                        }}>
                            <button 
                                onClick={() => { setView('signin'); setError(null) }}
                                style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: 'var(--color-text)',
                                    fontSize: '20px',
                                    fontFamily: 'var(--font-sans)',
                                    textDecoration: view === 'signin' ? 'underline' : 'none',
                                    textUnderlineOffset: '4px',
                                    opacity: view === 'signin' ? 1 : 0.5
                                }}
                            >
                                sign in
                            </button>
                            <button 
                                onClick={() => { setView('register'); setError(null)}}
                                style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: 'var(--color-text)',
                                    fontSize: '20px',
                                    fontFamily: 'var(--font-sans)',
                                    textDecoration: view === 'register' ? 'underline' : 'none',
                                    textUnderlineOffset: '4px',
                                    opacity: view === 'register' ? 1 : 0.5
                                }}
                            >
                                register
                            </button>
                        </div>
                    </div>


                    {/* Form Container */}
                    <form 
                        onSubmit={handleSubmit}
                        style={{
                            width: '100%',
                            maxWidth: '360px',
                            background: '#fff',
                            border: '1px solid #e5e4e7',
                            borderRadius: '8px',
                            padding: '32px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '20px',
                            boxShadow: 'rgba(0, 0, 0, 0.05) 0 4px 6px -2px'
                        }}
                    >
                        {/* OAuth Buttons (Only visible on register based on Figma) */}
                        {view === 'register' && (
                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button type="button" style={oauthButtonStyle}>GitHub</button>
                                <button type="button" style={oauthButtonStyle}>Google</button>
                            </div>
                        )}

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <label style={labelStyle}>Email</label>
                            <input 
                                type="email" 
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="Value"
                                required
                                style={inputStyle} 
                            />
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <label style={labelStyle}>Password</label>
                            <input 
                                type="password" 
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Value"
                                required
                                style={inputStyle} 
                            />
                        </div>

                        {/* Strict Penetration Testing Consent Checkbox */}
                        {view === 'register' && (
                            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', marginTop: '4px' }}>
                                <input 
                                    type="checkbox" 
                                    id="consent"
                                    checked={consent}
                                    onChange={(e) => setConsent(e.target.checked)}
                                    style={{ marginTop: '4px', cursor: 'pointer' }}
                                />
                                <label htmlFor="consent" style={{ fontSize: '13px', color: 'var(--color-text)', lineHeight: 1.4, cursor: 'pointer' }}>
                                    I own or have explicit permission to test any URL I submit to shovl
                                </label>
                            </div>
                        )}

                        {/* Step 5 — error message */}
                        {error && (
                            <p style={{ color: 'red', fontFamily: 'var(--font-mono)', fontSize: '13px', margin: 0 }}>
                                {error}
                            </p>
                        )}
                        

                        <button 
                            type="submit"
                            disabled={view === 'register' && !consent}
                            style={{
                                background: (view === 'register' && !consent) ? '#ccc' : '#111',
                                color: '#fff',
                                padding: '12px',
                                border: 'none',
                                borderRadius: '4px',
                                fontFamily: 'var(--font-sans)',
                                fontWeight: 600,
                                fontSize: '15px',
                                cursor: (view === 'register' && !consent) ? 'not-allowed' : 'pointer',
                                marginTop: '8px',
                                transition: 'background 0.2s ease'
                            }}
                        >
                            {loading ? 'loading...' : view === 'signin' ? 'Sign In' : 'Register'}
                        </button>

                        {view === 'signin' && (
                            <a href="#" style={{ fontSize: '13px', color: 'var(--color-text)', textDecoration: 'underline', marginTop: '4px' }}>
                                Forgot password?
                            </a>
                        )}
                    </form>

                </div>
            </div>
        </PageShell>
    )
}

// Extracted styles to keep the JSX clean
const labelStyle = {
    fontFamily: 'var(--font-sans)',
    fontSize: '14px',
    color: 'var(--color-text)'
}

const inputStyle = {
    padding: '10px 12px',
    border: '1px solid #e5e4e7',
    borderRadius: '6px',
    fontSize: '14px',
    fontFamily: 'var(--font-sans)',
    outline: 'none'
}

const oauthButtonStyle = {
    flex: 1,
    padding: '10px',
    background: '#111',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontFamily: 'var(--font-sans)',
    fontSize: '14px'
}