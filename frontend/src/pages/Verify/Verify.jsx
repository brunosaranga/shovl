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
import { extractHostname, isPracticeTarget } from "../../lib/targets";
import { fill } from "../../lib/text";
import styles from "./Verify.module.css";

// Prove you own a domain (DNS TXT record), then the scan starts.
// Arrives with the scan options in location.state (from the landing page or sign-in).
export default function Verify() {
    const { verify } = useContent();
    const navigate = useNavigate();
    const location = useLocation();
    const options = location.state?.url ? location.state : null;
    const targetUrl = options?.url || "";
    const hostname = extractHostname(targetUrl);
    const practice = isPracticeTarget(targetUrl);

    const { domain, loading, error } = useDomainSetup(options && !practice ? hostname : null);
    const [failed, setFailed] = useState(false);

    // Verified on an earlier visit: skip straight to the scan.
    useEffect(() => {
        if (domain?.verified) navigate("/scan/running", { state: options, replace: true });
    }, [domain, options, navigate]);

    if (!options) return <Navigate to="/" replace />;
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
                        <VerifyIntro targetUrl={targetUrl} />
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
                            onVerified={() => navigate("/scan/running", { state: options })}
                            onFailed={() => setFailed(true)}
                        />
                    </>
                ) : null}
            </PageBody>
        </>
    );
}
