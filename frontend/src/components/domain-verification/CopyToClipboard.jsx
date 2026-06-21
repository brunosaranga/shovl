import { useState } from 'react'

// Renders the dark terminal panel showing the token, with copy-to-clipboard behavior.
export default function CopyToClipboard({ token }) {
    const [copied, setCopied] = useState(false)

    const handleCopy = () => {
        navigator.clipboard.writeText(token)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div className="dns-token-terminal">
            <code className="dns-token-text">
                {token}
            </code>

            <button
                onClick={handleCopy}
                className={`dns-copy-button${copied ? ' is-copied' : ''}`}
            >
                {copied ? 'copied!' : 'copy'}
            </button>
        </div>
    )
}