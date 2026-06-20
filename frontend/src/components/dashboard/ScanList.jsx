import React from 'react'
import scans from '../common/MockScans'
// import { useState, useEffect } from 'react'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import getRiskColor from '../common/RiskColors'


{/* Scan Items / Queue */}
export default function ScanList({ scanProgress, setScanProgress, expandedScanId, setExpandedScanId }) {
    const navigate = useNavigate()
    useEffect(() => {
    if (scanProgress < 100) {
        const timer = setTimeout(() => setScanProgress(prev => prev + 1), 1000)
        return () => clearTimeout(timer)
    }
}, [scanProgress, setScanProgress])
    
    return (
        <div className="scans-queue-container">
            <h2 className="scans-queue-title">
                your scans
            </h2>

            {scans.map((scan) => (
                <div key={scan.id} className="scan-item-card">
                    {/* Row Header */}
                    <div className={`scan-item-header ${expandedScanId === scan.id ? 'header-expanded' : 'header-collapsed'}`}>
                        <div className="scan-item-left-group">
                            <span style={{
                                background: scan.status === 'scanning' ? 'var(--color-accent)' : '#f1f1f1',
                            }} className="scan-status-badge">
                                {scan.status}
                            </span>
                            <span className="scan-target-name">{scan.target}</span>
                        </div>

                        <div className="scan-item-right-group">
                            <span className="scan-date-text">{scan.date}</span>
                            <span style={{
                                background: getRiskColor(scan.risk),
                                color: scan.risk === 'MED' ? '#111' : '#fff',
                            }} className="scan-risk-badge">
                                !!! {scan.risk}
                            </span>
                            <button
                                onClick={() => setExpandedScanId(expandedScanId === scan.id ? null : scan.id)}
                                style={{
                                    transform: expandedScanId === scan.id ? 'rotate(90deg)' : 'rotate(0deg)',
                                }}
                                className="scan-toggle-button"
                            >
                                ➔
                            </button>
                        </div>
                    </div>

                    {/* Expanded Area - Active Scanning details */}
                    {expandedScanId === scan.id && scan.status === 'scanning' && (
                        <div className="expanded-scanning-panel">
                            <div className="progress-label-container">
                                <span className="progress-text-label">progress</span>
                                <span className="progress-percentage-value">{scanProgress}%</span>
                            </div>
                            <div className="progress-bar-track">
                                <div style={{
                                    width: `${scanProgress}%`,
                                }} className="progress-bar-fill" />
                            </div>

                            <span className="terminal-label">terminal output</span>
                            <div className="terminal-window">
                                {scan.logs.map((log, idx) => (
                                    <div key={idx} style={{ opacity: idx === scan.logs.length - 1 ? 1 : 0.7 }}>
                                        {log}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Expanded Area - Completed Scan summary */}
                    {expandedScanId === scan.id && scan.status === 'completed' && (
                        <div className="expanded-completed-panel">
                            <span className="summary-label">scan summary</span>
                            <div>✓ No critical endpoint vulnerabilities detected.</div>
                            <div className="summary-bullet-item">• Automated payload fuzzing completed successfully.</div>
                            <button 
                                onClick={() => navigate(`/scan/results/${scan.id}`)}
                                className="view-findings-button"
                            >
                                view vulnerability findings
                            </button>
                        </div>
                    )}
                </div>
            ))}
        </div>
    )
}