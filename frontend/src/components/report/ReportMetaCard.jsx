import { PrimaryButton } from '../layout/Buttons'

// Top summary strip — target, runtime, re-run action.
// Self-contained for now, same as ScanStats; wire to real scan data later.
export default function ReportMetaCard() {
    return (
        <div className="report-meta-card">
            <div className="report-meta-details">
                <div className="report-meta-line">
                    <span className="report-meta-label">target: </span>
                    <span>api.example.com</span>
                </div>
                <div className="report-meta-line">
                    <span className="report-meta-label">runtime: </span>
                    <span>Jun 21 2026 00:12:44</span>
                </div>
            </div>
            <PrimaryButton>re-run scan</PrimaryButton>
        </div>
    )
}