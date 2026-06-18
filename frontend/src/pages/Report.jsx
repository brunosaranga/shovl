import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { scansAPI } from '../api/client'
import Navbar from '../components/layout/Navbar'
import GroundCanvas from '../components/layout/GroundCanvas'
import VulnMatrix from '../components/report/VulnMatrix'
import FindingCard from '../components/report/FindingCard'
import RiskBlock from '../components/report/RiskBlock'
import RemediationSummary from '../components/report/RemediationSummary'

export default function Report() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [scan, setScan] = useState(null)

  useEffect(() => {
    scansAPI.get(id).then(res => setScan(res.data))
  }, [id])

  const handleDownloadPDF = async () => {
    const res = await scansAPI.pdf(id)
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `shovl_report_${id}.pdf`
    a.click()
  }

  if (!scan) return <div style={{ padding: '80px', textAlign: 'center' }}>Loading...</div>

  const report = scan.results
  const meta = report?.meta
  const findings = report?.findings || []
  const summary = report?.summary || {}

  return (
    <div style={{ position: 'relative', minHeight: '100vh', overflow: 'hidden' }}>
      <Navbar title="report">
        <button
          onClick={() => navigate('/dashboard')}
          style={{
            position: 'absolute', left: '40px',
            background: 'var(--color-accent)', color: '#111',
            fontWeight: 700, padding: '8px 16px',
            border: 'none', borderRadius: '4px', cursor: 'pointer',
          }}
        >
          ← Back to Dashboard
        </button>
      </Navbar>

      <div style={{ padding: '40px 80px', paddingBottom: '300px' }}>

        {/* Save PDF */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px' }}>
          <button
            onClick={handleDownloadPDF}
            style={{
              background: 'var(--color-accent)', color: '#111',
              fontWeight: 700, padding: '10px 20px',
              border: 'none', borderRadius: '4px', cursor: 'pointer',
            }}
          >
            Save PDF
          </button>
        </div>

        {/* Scan meta */}
        <div style={{
          border: '1px solid var(--color-border)', borderRadius: '4px',
          padding: '20px', marginBottom: '24px',
          display: 'flex', flexDirection: 'column', gap: '6px',
        }}>
          <p style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: '15px' }}>
            {meta?.target}
          </p>
          <p style={{ fontSize: '12px', color: 'var(--color-muted)' }}>
            Scan timestamp: {meta?.scanned_at}
          </p>
          <p style={{ fontSize: '12px', color: 'var(--color-muted)' }}>
            Total Checks: {meta?.total_checks}
          </p>
        </div>

        {/* Risk block */}
        <RiskBlock riskScore={meta?.risk_score} summary={summary} />

        {/* Vulnerability matrix */}
        <VulnMatrix summary={summary} />

        {/* Findings */}
        <h2 style={{ fontSize: '20px', fontWeight: 800, margin: '32px 0 16px' }}>
          Findings
        </h2>
        {findings.map((finding, i) => (
          <FindingCard key={i} finding={finding} />
        ))}

        {/* Remediation summary */}
        <RemediationSummary findings={findings} />

        {/* Footer */}
        <div style={{
          marginTop: '48px', textAlign: 'center',
          fontSize: '11px', color: 'var(--color-muted)',
        }}>
          shovl · Hinajuju Dynama · 2026 · This report is confidential.
        </div>
      </div>

      <GroundCanvas height={220} />
    </div>
  )
}