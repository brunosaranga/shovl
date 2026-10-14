import { useEffect, useState } from "react";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import SettingsSection, { SettingsRow } from "../../components/sections/settings/SettingsSection/SettingsSection";
import { useSession } from "../../context/SessionContext";
import { useContent } from "../../hooks/useContent";
import { domainsApi } from "../../lib/api";
import { fill } from "../../lib/text";
import styles from "./Settings.module.css";

// Only what the backend supports today: the account email, domains, and the plan's allowance.
// (Editing, API keys and account deletion come back when their endpoints exist.)
export default function Settings() {
    const { settings, common } = useContent();
    const { user, allowance } = useSession();
    const [domains, setDomains] = useState(null);

    useEffect(() => {
        let cancelled = false;
        domainsApi
            .list()
            .then(({ data }) => !cancelled && setDomains(Array.isArray(data) ? data : []))
            .catch(() => !cancelled && setDomains([]));
        return () => {
            cancelled = true;
        };
    }, []);

    return (
        <>
            <PageMeta title={settings.meta} />
            <NavCenter>
                <PageTitle>{settings.pageTitle}</PageTitle>
            </NavCenter>

            <PageBody width="wide" gap="lg" mono>
                <SettingsSection title={settings.account.title}>
                    <SettingsRow label={settings.account.email} value={user?.email || common.loading} />
                </SettingsSection>

                <SettingsSection title={settings.domains.title}>
                    {domains === null ? <p>{common.loading}</p> : null}
                    {domains?.length === 0 ? <p>{settings.domains.empty}</p> : null}
                    {domains?.map((domain) => (
                        <SettingsRow
                            key={domain.id}
                            label={domain.hostname}
                            value={
                                domain.verified ? (
                                    <span className={styles.verified} aria-label={settings.domains.verifiedLabel}>
                                        {settings.domains.verified}
                                    </span>
                                ) : (
                                    <span className={styles.pending}>{settings.domains.pending}</span>
                                )
                            }
                        />
                    ))}
                </SettingsSection>

                <SettingsSection title={settings.plan.title}>
                    <SettingsRow label={settings.plan.plan} value={settings.plan.free} />
                    <SettingsRow
                        label={settings.plan.scans}
                        value={allowance ? fill(settings.plan.remaining, allowance) : settings.plan.unlimited}
                    />
                </SettingsSection>
            </PageBody>
        </>
    );
}
