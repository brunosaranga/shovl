import { useState, useRef } from 'react'
import { useAuth } from '../context/AuthContext'

import PageShell from '../components/layout/PageShell'
import URLInput from '../components/scan/URLInput'
import { PrimaryButton } from '../components/layout/Buttons'
import ToggleRow from '../components/landing/ToggleRow'
import BrandHero from '../components/landing/BrandHero'
import useScan from '../components/scan/HandleScan'

export default function Landing() {
    const [url, setUrl] = useState('')
    const [verbose, setVerbose] = useState(false)
    const [generateReport, setGenerateReport] = useState(true)
    const [suggestFix, setSuggestFix] = useState(false)
    const [urlError, setUrlError] = useState(false)
    const urlInputRef = useRef(null)
    const { accessToken } = useAuth()
    const { startScan } = useScan()


    const handleScanTrigger = () => {
        startScan({
            url,
            verbose,
            generateReport,
            suggestFix,
            setUrlError,
            urlInputRef
        })
    }


    // Wrap the decoupled landing input component to pass into centerElement
    const centerInputSlot = (
        <URLInput
            ref={urlInputRef}
            url={url}
            setUrl={setUrl}
            onSearchSubmit={handleScanTrigger}
            hasError={urlError}
        />
    )

    return (
        <PageShell
            centerElement={centerInputSlot}
        >
            <div className='landing'>
                <ToggleRow
                    verbose={verbose} setVerbose={setVerbose}
                    generateReport={generateReport} setGenerateReport={setGenerateReport}
                    suggestFix={suggestFix} setSuggestFix={setSuggestFix}
                />

                <BrandHero />

                <div className='primary-action-button-container'>
                    <PrimaryButton onClick={handleScanTrigger}>
                        dig deeper
                    </PrimaryButton>
                </div>
            </div>
        </PageShell>
    )
}