import React from 'react'

// Press/hover feedback lives in .button-primary / :active in global.css —
// no JS-driven inline style mutation needed.
export function PrimaryButton({ children, onClick, className = '', ...rest }) {
    return (
        <button
            className={`button-primary ${className}`.trim()}
            onClick={onClick}
            {...rest}
        >
            {children}
        </button>
    )
}