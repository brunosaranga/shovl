import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import PageTitle from '../components/common/PageTitle'
import PageShell from '../components/layout/PageShell'
import { PrimaryButton } from '../components/layout/Buttons'


import getRiskColor from '../components/common/RiskColors.jsx'
import scans from '../components/common/MockScans.jsx'


export default function Dashboard() {
    const navigate = useNavigate()
    const [expandedScanId, setExpandedScanId] = useState(null)
    const [scanProgress, setScanProgress] = useState(60) // <--- Added missing state definition


    return (
        <PageShell centerElement={<PageTitle>dashboard</PageTitle>}>
            <div style={{
                maxWidth: '960px',
                margin: '0 auto',
                paddingTop: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '32px',
                fontFamily: 'var(--font-mono)'
            }}>
                
                {/* Executive View / High-Level Stats & CTA */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#fff',
                    border: '3px solid var(--color-text)',
                    padding: '20px 24px',
                    boxShadow: '6px 6px 0px var(--color-text)'
                }}>
                    <div style={{ display: 'flex', gap: '32px', alignItems: 'center' }}>
                        <div>
                            <span style={{ fontSize: '12px', color: 'var(--color-muted)', textTransform: 'lowercase', display: 'block' }}>Active Scans</span>
                            <span style={{ fontSize: '24px', fontWeight: 900, color: 'var(--color-text)' }}>
                                {scans.filter(s => s.status === 'scanning').length}
                            </span>
                        </div>
                        <div style={{ borderLeft: '2px solid var(--color-text)', height: '40px' }} />
                        <div>
                            <span style={{ fontSize: '12px', color: 'var(--color-muted)', textTransform: 'lowercase', display: 'block' }}>Threat Alerts</span>
                            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                                <span style={{ background: '#ff4d4f', color: '#fff', padding: '2px 6px', fontSize: '10px', fontWeight: 800 }}>CRIT: 1</span>
                                <span style={{ background: '#ff9f43', color: '#fff', padding: '2px 6px', fontSize: '10px', fontWeight: 800 }}>HIGH: 1</span>
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={() => navigate('/')}
                        style={{
                            background: 'var(--color-accent)',
                            color: 'var(--color-text)',
                            fontFamily: 'var(--font-display)',
                            fontWeight: 900,
                            fontSize: '16px',
                            padding: '10px 20px',
                            border: '2px solid var(--color-text)',
                            cursor: 'pointer',
                            boxShadow: '4px 4px 0px var(--color-text)',
                            transition: 'all 0.1s ease',
                            textTransform: 'lowercase'
                        }}
                        onMouseDown={(e) => {
                            e.currentTarget.style.transform = 'translate(2px, 2px)'
                            e.currentTarget.style.boxShadow = '1px 1px 0px var(--color-text)'
                        }}
                        onMouseUp={(e) => {
                            e.currentTarget.style.transform = 'translate(0px, 0px)'
                            e.currentTarget.style.boxShadow = '4px 4px 0px var(--color-text)'
                        }}
                    >
                        + new scan
                    </button>
                </div>

                {/* Scan Items / Queue */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <h2 style={{ 
                        fontFamily: 'var(--font-display)', 
                        fontSize: '22px', 
                        letterSpacing: '-1px', 
                        margin: 0, 
                        textTransform: 'lowercase' 
                    }}>
                        your scans
                    </h2>

                    {scans.map((scan) => (
                        <div key={scan.id} style={{
                            border: '3px solid var(--color-text)',
                            background: '#fff',
                            boxShadow: '5px 5px 0px var(--color-text)',
                            overflow: 'hidden'
                        }}>
                            {/* Row Header */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '16px 20px',
                                borderBottom: expandedScanId === scan.id ? '2px solid var(--color-text)' : 'none'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                    <span style={{
                                        background: scan.status === 'scanning' ? 'var(--color-accent)' : '#f1f1f1',
                                        padding: '4px 10px',
                                        fontSize: '11px',
                                        fontWeight: 800,
                                        textTransform: 'lowercase',
                                        border: '1px solid var(--color-text)'
                                    }}>
                                        {scan.status}
                                    </span>
                                    <span style={{ fontWeight: 700, fontSize: '15px' }}>{scan.target}</span>
                                </div>

                                <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                                    <span style={{ fontSize: '13px', color: 'var(--color-muted)' }}>{scan.date}</span>
                                    <span style={{
                                        background: getRiskColor(scan.risk),
                                        color: scan.risk === 'MED' ? '#111' : '#fff',
                                        padding: '4px 8px',
                                        fontSize: '11px',
                                        fontWeight: 900,
                                        border: '1px solid var(--color-text)'
                                    }}>
                                        !!! {scan.risk}
                                    </span>
                                    <button
                                        onClick={() => setExpandedScanId(expandedScanId === scan.id ? null : scan.id)}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            fontSize: '16px',
                                            fontWeight: 900,
                                            transform: expandedScanId === scan.id ? 'rotate(90deg)' : 'rotate(0deg)',
                                            transition: 'transform 0.15s ease'
                                        }}
                                    >
                                        ➔
                                    </button>
                                </div>
                            </div>

                            {/* Expanded Area - Active Scanning details */}
                            {expandedScanId === scan.id && scan.status === 'scanning' && (
                                <div style={{ background: '#fcfcfc', padding: '20px', borderBottom: '2px solid var(--color-text)' }}>
                                    <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                        <span style={{ textTransform: 'lowercase' }}>progress</span>
                                        <span style={{ fontWeight: 700 }}>{scanProgress}%</span>
                                    </div>
                                    <div style={{
                                        width: '100%',
                                        height: '12px',
                                        border: '2px solid var(--color-text)',
                                        background: '#fff',
                                        padding: '1px',
                                        marginBottom: '16px'
                                    }}>
                                        <div style={{
                                            height: '100%',
                                            background: 'var(--color-accent)',
                                            width: `${scanProgress}%`,
                                            transition: 'width 0.4s ease'
                                        }} />
                                    </div>

                                    <span style={{ fontSize: '11px', color: 'var(--color-muted)', display: 'block', marginBottom: '6px', textTransform: 'lowercase' }}>terminal output</span>
                                    <div style={{
                                        background: 'var(--color-text)',
                                        color: '#fff',
                                        padding: '12px',
                                        fontSize: '12px',
                                        fontFamily: 'var(--font-mono)',
                                        maxHeight: '120px',
                                        overflowY: 'auto',
                                        border: '2px solid var(--color-text)'
                                    }}>
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
                                <div style={{ background: '#fcfcfc', padding: '20px', borderBottom: '2px solid var(--color-text)', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                                    <span style={{ textTransform: 'lowercase', color: 'var(--color-muted)', fontSize: '11px' }}>scan summary</span>
                                    <div>✓ No critical endpoint vulnerabilities detected.</div>
                                    <div style={{ color: 'var(--color-muted)' }}>• Automated payload fuzzing completed successfully.</div>
                                    <button 
                                        onClick={() => navigate(`/scan/results/${scan.id}`)}
                                        style={{
                                            alignSelf: 'flex-start',
                                            marginTop: '8px',
                                            background: '#111',
                                            color: '#fff',
                                            padding: '8px 16px',
                                            fontSize: '12px',
                                            border: 'none',
                                            cursor: 'pointer',
                                            textTransform: 'lowercase'
                                        }}
                                    >
                                        view vulnerability findings
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Pagination */}
                <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '16px', fontSize: '14px', fontWeight: 700 }}>
                    <span style={{ border: '2px solid var(--color-text)', padding: '6px 12px', background: 'var(--color-accent)' }}>1</span>
                    <span style={{ border: '2px solid var(--color-text)', padding: '6px 12px', background: '#fff' }}>2</span>
                    <span style={{ border: '2px solid var(--color-text)', padding: '6px 12px', background: '#fff' }}>3</span>
                </div>

            </div>
        </PageShell>
    )
}