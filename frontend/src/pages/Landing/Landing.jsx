import { useRef, useState } from "react";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import UrlInput from "../../components/forms/UrlInput/UrlInput";
import BrandHeader from "../../components/sections/landing/BrandHeader/BrandHeader";
import ScanOptions from "../../components/sections/landing/ScanOptions/ScanOptions";
import BrandHero from "../../components/sections/landing/BrandHero/BrandHero";
import LaunchPanel from "../../components/sections/landing/LaunchPanel/LaunchPanel";
import { useSession } from "../../context/SessionContext";
import { useContent } from "../../hooks/useContent";
import { MOBILE_QUERY, useMediaQuery } from "../../hooks/useMediaQuery";
import { useScanLauncher } from "../../hooks/useScanLauncher";
import { useScanOptions } from "../../hooks/useScanOptions";
import { fill } from "../../lib/text";
import styles from "./Landing.module.css";

export default function Landing() {
    const { landing } = useContent();
    const { status, allowance } = useSession();
    const isMobile = useMediaQuery(MOBILE_QUERY);
    const { launch, urlError, consentError, launchError, busy, clearUrlError } = useScanLauncher();

    const [url, setUrl] = useState("");
    // Remembered until a refresh (hooks/useScanOptions.js).
    const [options, setOptions] = useScanOptions();
    const [consent, setConsent] = useState(false);
    const urlRef = useRef(null);
    const consentRef = useRef(null);

    const onLaunch = async () => {
        const result = await launch({ url, options, consent });
        if (result?.focus === "url") urlRef.current?.focus();
        if (result?.focus === "consent") consentRef.current?.focus();
    };

    const onUrlChange = (value) => {
        setUrl(value);
        if (urlError) clearUrlError();
    };

    let allowanceText = null;
    if (status === "anonymous") allowanceText = landing.allowance.anonymous;
    else if (allowance) allowanceText = fill(status === "guest" ? landing.allowance.guest : landing.allowance.registered, allowance);

    const urlInput = <UrlInput value={url} onChange={onUrlChange} onSubmit={onLaunch} error={urlError} inputRef={urlRef} />;

    return (
        <>
            <PageMeta title={landing.meta} />

            {/* Desktop: the URL input lives in the navbar. Mobile: in the page. */}
            {isMobile ? <BrandHeader /> : <NavCenter>{urlInput}</NavCenter>}

            <div className={styles.landing}>
                <ScanOptions options={options} onChange={setOptions} />

                {isMobile ? <div className={styles.mobileInput}>{urlInput}</div> : null}

                <BrandHero />

                <LaunchPanel
                    onLaunch={onLaunch}
                    busy={busy}
                    showConsent={status === "anonymous"}
                    consent={consent}
                    onConsentChange={setConsent}
                    consentError={consentError}
                    consentRef={consentRef}
                    allowanceText={allowanceText}
                    error={launchError}
                    showExamples={status !== "registered"}
                    onPickExample={(example) => {
                        onUrlChange(example);
                        urlRef.current?.focus();
                    }}
                />

            </div>
        </>
    );
}
