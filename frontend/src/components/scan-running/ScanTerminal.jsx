// Scrolling log stream output terminal.
export default function ScanTerminal({ logs, isComplete }) {
    return (
        <div className="scan-terminal">
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