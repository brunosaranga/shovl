import shovlLogo from '../../assets/shovl-logo.svg'

// Status title, target label, pause/stop controls, and spinning logo.
export default function ScanHeader({ targetUrl, isPaused, onTogglePause, onStop }) {
    return (
        <div className="scan-header">
            <div className="scan-header-title-group">
                <h1 className="scan-header-title">digging deeper...</h1>
                <p className="scan-header-target">Targeting: {targetUrl}</p>
            </div>

            <div className="scan-header-controls">

                {/* Pause / Play */}
                <button
                    onClick={onTogglePause}
                    className="scan-control-button"
                >
                    <span className="scan-control-icon">
                        {isPaused ? '▶' : '||'}
                    </span>
                </button>

                {/* Stop */}
                <button
                    onClick={onStop}
                    className="scan-control-button is-stop"
                >
                    <span className="scan-stop-square" />
                </button>

                {/* Spinning logo */}
                <div className="scan-logo-box">
                    <img
                        src={shovlLogo}
                        alt="scan active"
                        className={`scan-logo-image ${isPaused ? 'is-paused' : ''}`}
                    />
                </div>

            </div>
        </div>
    )
}