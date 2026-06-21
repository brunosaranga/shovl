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
            />
        </div>
    )
})

export default URLInput