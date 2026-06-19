import React from 'react'

export default function PageTitle({ children }) {
    return (
        <h1 style={{
            fontFamily: 'var(--font-display)',
            fontSize: '32px',
            fontWeight: 900,
            margin: 0,
            letterSpacing: '-1.5px',
            color: 'var(--color-text)',
            textTransform: 'lowercase'
        }}>
            {children}
        </h1>
    )
}