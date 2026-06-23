import { useRef, useEffect } from 'react'

// Scrolling log stream output terminal. Auto-scrolls to the newest line as
// the stream comes in, and stays scrollable so you can read back through it.
export default function ScanTerminal({ logs, isComplete }) {
    const scrollRef = useRef(null)

    useEffect(() => {
        const el = scrollRef.current
        if (el) el.scrollTop = el.scrollHeight
    }, [logs, isComplete])

    return (
        <div className="scan-terminal" ref={scrollRef}>
            {logs.map((log, index) => (
                <div
                    key={index}
                    className={`scan-terminal-line ${index === logs.length - 1 ? 'is-latest' : ''}`}
                >
                    {log}
                </div>
            ))}
            {isComplete && (
                <div className="scan-terminal-complete">
                    {'>> scan complete! redirecting to vulnerability results...'}
                </div>
            )}
        </div>
    )
}