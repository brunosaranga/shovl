{/* Navbar */}
            <nav style={{
                display: 'flex', 
                alignItems: 'center',
                justifyContent: 'space-between',
                height: '64px', 
                padding: '0 40px',
                // borderBottom: '2px solid #111111',
                position: 'relative', 
                zIndex: 10, 
                background: 'white',
                width: '100%'
            }}>

                {/* Brand Logo Asset */}
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

                {/* Central URL Input Module */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ 
                        fontFamily: 'var(--font-display)', 
                        fontWeight: 900, 
                        fontSize: '14px' 
                    }}>
                        URL:
                    </span>
                    <input
                        value={url}
                        onChange={e => setUrl(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleScan()}
                        placeholder="paste your API URL..."
                        style={{
                            width: '320px', 
                            height: '38px',
                            // background: '#111111',
                            color: 'var(--color-text)',
                            border: '1px solid var(--color-text)',
                            padding: '0 20px',
                            fontFamily: 'var(--font-mono)', 
                            fontSize: '13px',
                            outline: 'none'
                        }}
                    />
                </div>

                {/* Interactive Account Avatar Action */}
                <div
                    onClick={() => navigate('/signin')}
                    style={{
                        width: '40px', 
                        height: '40px', 
                        borderRadius: '50%',
                        border: '2px solid #111',
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        cursor: 'pointer',
                        overflow: 'hidden',
                        background: '#fff',
                        transition: 'transform 0.1s ease'
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