import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

import PageShell from '../components/layout/PageShell'
import URLInput from '../components/scan/URLInput'
import { PrimaryButton } from '../components/layout/Buttons'
import ToggleRow from '../components/landing/ToggleRow'
import BrandHero from '../components/landing/BrandHero.jsx'

export default function Landing() {
    const [url, setUrl] = useState('')
    const [verbose, setVerbose] = useState(false)
    const [generateReport, setGenerateReport] = useState(true)
    const [suggestFix, setSuggestFix] = useState(false)
    const [urlError, setUrlError] = useState(false)
    const urlInputRef = useRef(null)
    const { accessToken } = useAuth()
    const navigate = useNavigate()

    // first it goes to domain verification where it verifies if user owns domain, examining the passed in URL
    const handleScan = () => {
        if (!url) {
            // give visible feedback instead of failing silently — the URL field
            // lives up in the navbar, easy to miss from the button down here
            setUrlError(true)
            urlInputRef.current?.focus()
            setTimeout(() => setUrlError(false), 1500)
            return
        }
        if (!accessToken) {
            navigate('/verify', { state: { pendingScan: { url, verbose, generateReport, suggestFix } } })
            return
        }
        // if authenticated, and the same verified domain is examined, proceed to begin the scan
        navigate('/scan/new', { state: { url, verbose, generateReport, suggestFix } })
    }

    // Wrap the decoupled landing input component to pass into centerElement
    const centerInputSlot = (
        <URLInput
            ref={urlInputRef}
            url={url}
            setUrl={setUrl}
            onSearchSubmit={handleScan}
            hasError={urlError}
        />
    )

    return (
        <PageShell
            title="landing"
            isLanding={true}
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
                    <PrimaryButton onClick={handleScan}>
                        dig deeper
                    </PrimaryButton>
                </div>
            </div>
        </PageShell>
    )
}