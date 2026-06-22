// Brutalist stepped progress bar.
export default function ScanProgressBar({ progress }) {
    return (
        <div className="scan-progress-track">
            <div
                className="scan-progress-fill"
                style={{ width: `${progress}%` }}
            />
        </div>
    )
}