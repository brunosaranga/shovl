import FindingItem from './FindingItem'

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

export default function FindingsList({ openFindingId, setOpenFindingId }) {
    const toggleFinding = (id) => {
        setOpenFindingId(openFindingId === id ? null : id)
    }

    return (
        <div className="findings-deck">
            <h3 className="findings-deck-title">vulnerability findings</h3>

            {findingsData.map((item) => (
                <FindingItem
                    key={item.id}
                    item={item}
                    isExpanded={openFindingId === item.id}
                    onToggle={() => toggleFinding(item.id)}
                />
            ))}
        </div>
    )
}