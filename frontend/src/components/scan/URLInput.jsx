import React from 'react'

export default function URLInput({ url, setUrl, onSearchSubmit }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ 
                fontFamily: 'var(--font-display)', 
                fontWeight: 900, 
                fontSize: '14px',
                color: 'var(--color-text)' 
            }}>
                URL:
            </span>
            <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && onSearchSubmit()}
                placeholder="paste your API URL..."
                style={{
                    width: '320px', 
                    height: '38px',
                    color: 'var(--color-text)',
                    border: '2px solid var(--color-text)',
                    padding: '0 20px',
                    fontFamily: 'var(--font-mono)', 
                    fontSize: '13px',
                    outline: 'none'
                }}
            />
        </div>
    )
}