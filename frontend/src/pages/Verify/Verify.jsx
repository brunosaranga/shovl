import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import Alert from "../../components/ui/Alert/Alert";
import VerifyIntro from "../../components/sections/verify/VerifyIntro/VerifyIntro";
import DnsInstructions from "../../components/sections/verify/DnsInstructions/DnsInstructions";
import VerifyAction from "../../components/sections/verify/VerifyAction/VerifyAction";
import { useContent } from "../../hooks/useContent";
import { useDomainSetup } from "../../hooks/useDomainSetup";
import { useSoundCue } from "../../hooks/useSounds";
import { extractHostname, isPracticeTarget } from "../../lib/targets";
import { fill } from "../../lib/text";
import styles from "./Verify.module.css";

// Prove you own a domain (DNS TXT record). Two ways in, both through location.state:
//   scan:         { url, ...scan options } from the landing page or sign-in. Once verified,
//                 the scan starts.
//   verify only:  { verifyOnly: true, hostname, from } from the bell ("verify domain"). Once
//                 verified, back to `from`; no scan starts. A domain shovl watch's rule A put
//                 back to pending gets its paused watches restarted by the backend.
// No ambiance on this page (routes.jsx); errors still play the error cue.
export default function Verify() {
    const { verify } = useContent();
    const navigate = useNavigate();
    const location = useLocation();
    const verifyOnly = Boolean(location.state?.verifyOnly && location.state?.hostname);
    const options = !verifyOnly && location.state?.url ? location.state : null;
    const targetUrl = options?.url || "";
    const hostname = verifyOnly ? location.state.hostname : extractHostname(targetUrl);
    const backTo = verifyOnly ? location.state.from || "/dashboard" : null;
    const practice = !verifyOnly && isPracticeTarget(targetUrl);

    const { domain, loading, error } = useDomainSetup(verifyOnly || (options && !practice) ? hostname : null);
    const [failed, setFailed] = useState(false);
    useSoundCue("error", !loading && error ? error : null);

    // Already verified (an earlier visit, or another tab): straight on.
    useEffect(() => {
        if (!domain?.verified) return;
        if (verifyOnly) navigate(backTo, { replace: true });
        else navigate("/scan/running", { state: options, replace: true });
    }, [domain, options, verifyOnly, backTo, navigate]);

    if (!options && !verifyOnly) return <Navigate to="/" replace />;
    if (practice) return <Navigate to="/scan/running" state={options} replace />;

    const recordName = `_shovl-verify.${hostname}`;

    return (
        <>
            <PageMeta title={verify.meta} />
            <NavCenter>
                <PageTitle>{verify.pageTitle}</PageTitle>
            </NavCenter>

            <PageBody width="narrow" gap="lg" top="compact">
                {loading ? <p className={styles.status}>{fill(verify.settingUp, { hostname })}</p> : null}

                {!loading && error ? (
                    <Alert title={verify.setupFailed} role="alert">
                        <ul>
                            <li>{error}</li>
                        </ul>
                    </Alert>
                ) : null}

                {!loading && !error && domain && !domain.verified ? (
                    <>
                        <VerifyIntro targetUrl={verifyOnly ? hostname : targetUrl} />
                        {verifyOnly ? <p className={styles.status}>{verify.verifyOnlyNote}</p> : null}
                        <DnsInstructions recordName={recordName} token={domain.verification_token} />

                        {failed ? (
                            <Alert title={verify.failedTitle} role="alert">
                                <ul>
                                    {verify.failedReasons.map((reason) => (
                                        <li key={reason}>{fill(reason, { record: recordName })}</li>
                                    ))}
                                </ul>
                            </Alert>
                        ) : null}

                        <VerifyAction
                            domainId={domain.id}
                            onVerified={() =>
                                verifyOnly ? navigate(backTo, { replace: true }) : navigate("/scan/running", { state: options })
                            }
                            onFailed={() => setFailed(true)}
                        />
                    </>
                ) : null}
            </PageBody>
        </>
    );
}
