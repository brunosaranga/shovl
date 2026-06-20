import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import PageTitle from '../components/common/PageTitle'
import PageShell from '../components/layout/PageShell'
import { PrimaryButton } from '../components/layout/Buttons'
import ScanList from '../components/dashboard/ScanList.jsx'
import ScanStats from '../components/dashboard/ScansStats.jsx'


import getRiskColor from '../components/common/RiskColors.jsx'
import scans from '../components/common/MockScans.jsx'


export default function Dashboard() {
    const navigate = useNavigate()
    const [expandedScanId, setExpandedScanId] = useState(null)
    const [scanProgress, setScanProgress] = useState(60) // <--- Added missing state definition


    return (
        <PageShell
        centerElement={<PageTitle>dashboard</PageTitle>}>
            <div className='dashboard'>
                
                {/* Scan stats */}
                <ScanStats />

                {/* Scan Items / Queue */}
                <ScanList
                    scanProgress={scanProgress} 
                    setScanProgress={setScanProgress} 
                    expandedScanId={expandedScanId}
                    setExpandedScanId={setExpandedScanId}
                />

                {/* Pagination */}
                <div className="pagination-container">
                    <span className="pagination-page active-page">1</span>
                    <span className="pagination-page">2</span>
                    <span className="pagination-page">3</span>
                </div>

            </div>
        </PageShell>
    )
}