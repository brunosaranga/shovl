import React from 'react'

export default function AppFooter() {
    return (
        <div style={{
            position: 'absolute', 
            bottom: '10px',
            width: '100%', 
            textAlign: 'center',
            fontFamily: 'var(--font-sans)',
            fontSize: '13px',
            fontWeight: 700,
            color: 'var(--color-bg)',
            zIndex: 4,
            pointerEvents: 'none'
        }}>
            © 2026 Hinajuju Dynama. All Rights Reserved
        </div>
    )
}