import React, { forwardRef } from 'react'

const URLInput = forwardRef(function URLInput({ url, setUrl, onSearchSubmit, hasError = false }, ref) {
    return (
        <div className='url-input-container' style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ 
                fontFamily: 'var(--font-display)', 
                fontWeight: 900, 
                fontSize: '14px',
                color: 'var(--color-text)' 
            }}>
                URL:
            </span>
            <input
                ref={ref}
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && onSearchSubmit()}
                placeholder={hasError ? 'enter a URL first' : 'paste your API URL...'}
                className={hasError ? 'url-input-error' : 'url-input'}
                style={{
                    width: '320px', 
                    height: '38px',
                    color: 'var(--color-text)',
                    border: hasError ? '2px solid var(--severity-critical)' : '2px solid var(--color-text)',
                    padding: '0 20px',
                    fontFamily: 'var(--font-mono)', 
                    fontSize: '13px',
                    outline: 'none'
                }}
            />
        </div>
    )
})

export default URLInput