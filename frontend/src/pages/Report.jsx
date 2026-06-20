import React, { useState } from 'react'
import PageShell from '../components/layout/PageShell'
import PageTitle from '../components/common/PageTitle'

export default function Report() {
    // Manages expanding finding items smoothly
    const [openFindingId, setOpenFindingId] = useState(1)

    const toggleFinding = (id) => {
        setOpenFindingId(openFindingId === id ? null : id)
    }

    // High-fidelity sample dataset to seamlessly fill out the layout viewport space
    const findingsData = [
        {
            id: 1,
            title: "SQL Injection Vulnerability",
            severity: "critical",
            color: "var(--color-sev-critical)",
            path: "POST /api/v1/auth/login",
            desc: "User input supplied via login parameters directly vectors into a dynamic SQL command building chain without input purification parameters, enabling unauthorized query insertion executions.",
            code: "const query = `SELECT * FROM users WHERE user = '${req.body.user}' AND pass = '${req.body.pass}'`;\nconst result = await db.execute(query);"
        },
        {
            id: 2,
            title: "Insecure Direct Object Reference (IDOR)",
            severity: "high",
            color: "var(--color-sev-high)",
            path: "GET /api/v1/users/account/:id",
            desc: "The controller endpoint directly matches requested account identifier keys against core system databases without handling or validating consumer resource ownership checks.",
            code: "async function getUserData(req, res) {\n  const userProfile = await User.findById(req.params.id);\n  res.json(userProfile);\n}"
        },
        {
            id: 3,
            title: "Cross-Site Scripting (Stored XSS)",
            severity: "high",
            color: "var(--color-sev-high)",
            path: "POST /api/v1/comments/new",
            desc: "Unchecked client payloads persist directly into database records and are rendered back to end-users without escaping, allowing malicious script injection.",
            code: "/* Render sequence injection point */\n<div className=\"comment-text\">\n  <p dangerouslySetInnerHTML={{ __html: comment.body }} />\n</div>"
        },
        {
            id: 4,
            title: "Broken Object Level Authorization",
            severity: "medium",
            color: "var(--color-sev-medium)",
            path: "PUT /api/v1/documents/:docId",
            desc: "Document update functions lack proper authentication middleware checks, exposing critical company assets to modifications by guest or cross-tenant consumers.",
            code: "router.put('/documents/:docId', async (req, res) => {\n  const doc = await Document.update(req.params.docId, req.body);\n  return res.json(doc);\n});"
        },
        {
            id: 5,
            title: "Permissive CORS Policy Detected",
            severity: "low",
            color: "var(--color-sev-low)",
            path: "headers Configuration",
            desc: "Access-Control-Allow-Origin parameters utilize raw wildcard parameters ('*'), exposing cross-origin data structures to data exfiltration vulnerabilities.",
            code: "app.use(cors({\n  origin: '*',\n  methods: ['GET', 'POST']\n}));"
        }
    ]

    return (
        <PageShell centerElement={<PageTitle>report</PageTitle>}>
            <div className="report-container">
                
                {/* Meta Summary Card */}
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
                    <button className="button-primary">re-run scan</button>
                </div>

                {/* Severity Metric Distribution Row */}
                <div className="severity-matrix-grid">
                    <div className="severity-matrix-box">
                        <div className="severity-matrix-header" style={{ background: 'var(--color-text)' }}>Critical</div>
                        <div className="severity-matrix-count">1</div>
                    </div>
                    <div className="severity-matrix-box">
                        <div className="severity-matrix-header" style={{ background: 'var(--color-errors)' }}>High</div>
                        <div className="severity-matrix-count">2</div>
                    </div>
                    <div className="severity-matrix-box">
                        <div className="severity-matrix-header" style={{ background: 'var(--color-sev-high)' }}>Medium</div>
                        <div className="severity-matrix-count">1</div>
                    </div>
                    <div className="severity-matrix-box">
                        <div className="severity-matrix-header" style={{ background: 'var(--color-sev-medium)' }}>Low</div>
                        <div className="severity-matrix-count">1</div>
                    </div>
                    <div className="severity-matrix-box">
                        <div className="severity-matrix-header" style={{ background: 'var(--color-sev-low)' }}>Passed</div>
                        <div className="severity-matrix-count">14</div>
                    </div>
                </div>

                {/* Active Findings Structural List Container */}
                <div className="findings-deck">
                    <h3 className="findings-deck-title">vulnerability findings</h3>
                    
                    {findingsData.map((item) => {
                        const isExpanded = openFindingId === item.id
                        return (
                            <div key={item.id} className="finding-item-card">
                                {/* Accordion Click Header Toggle */}
                                <div 
                                    className={`finding-item-header ${isExpanded ? 'expanded' : ''}`}
                                    onClick={() => toggleFinding(item.id)}
                                >
                                    <div className="finding-title-block">
                                        <span 
                                            className="finding-badge-inline"
                                            style={{ backgroundColor: item.color }}
                                        >
                                            {item.severity}
                                        </span>
                                        <span className="finding-name-text">{item.title}</span>
                                    </div>
                                    <div className="finding-meta-aside">
                                        <span className="finding-path-label">{item.path}</span>
                                        <span className="finding-caret">{isExpanded ? '▲' : '▼'}</span>
                                    </div>
                                </div>

                                {/* Code Terminal Block details section */}
                                {isExpanded && (
                                    <div className="finding-expanded-body">
                                        <p className="finding-description-para">{item.desc}</p>
                                        <div className="finding-code-container">
                                            <span className="finding-code-header">Vulnerable Code Segment</span>
                                            <pre className="finding-code-block">
                                                <code>{item.code}</code>
                                            </pre>
                                        </div>
                                        <div className="finding-remediation-tip">
                                            <strong>remediation suggestion:</strong> Clean target variables via specialized input filtering routines or abstract operations beneath parameter-driven prepared data layer models.
                                        </div>
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>

            </div>
        </PageShell>
    )
}