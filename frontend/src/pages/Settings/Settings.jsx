import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import Breakable from "../../components/ui/Breakable/Breakable";
import SettingsSection, { SettingsRow } from "../../components/sections/settings/SettingsSection/SettingsSection";
import WatchSettings from "../../components/sections/settings/WatchSettings/WatchSettings";
import UnverifiedCache from "../../components/sections/settings/UnverifiedCache/UnverifiedCache";
import { useNotifications } from "../../context/NotificationsContext";
import { useSession } from "../../context/SessionContext";
import { useContent } from "../../hooks/useContent";
import { domainsApi, watchesApi } from "../../lib/api";
import { fill } from "../../lib/text";
import styles from "./Settings.module.css";

const asList = (data) => (Array.isArray(data) ? data : []);

// Only what the backend supports today: the account email, shovll watch, domains and the plan.
// (Editing, API keys and account deletion come back when their endpoints exist.)
//
// The domain and watch lists load together and reload after every change made here; the bell
// reloads with them, so a removed domain or a resumed watch leaves "needs action" at once.
export default function Settings() {
    const { settings, common } = useContent();
    const { user, allowance } = useSession();
    const { refresh: refreshBell } = useNotifications();
    // domains / watches: null while loading.
    const [lists, setLists] = useState({ domains: null, watches: null, failed: false });
    // Only the newest load may write: an older one finishing late must not win.
    const latest = useRef(0);

    // Promise callbacks, so the state is only set once the answer is in (never during the
    // effect that asked for it).
    const load = useCallback(() => {
        const ticket = ++latest.current;
        return Promise.all([domainsApi.list(), watchesApi.list()]).then(
            ([domains, watches]) => {
                if (ticket !== latest.current) return;
                setLists({ domains: asList(domains.data), watches: asList(watches.data), failed: false });
            },
            () => {
                if (ticket !== latest.current) return;
                setLists((current) => ({
                    domains: current.domains ?? [],
                    watches: current.watches ?? [],
                    failed: true,
                }));
            }
        );
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const changed = useCallback(() => Promise.all([load(), refreshBell()]), [load, refreshBell]);

    const verified = lists.domains?.filter((domain) => domain.verified) ?? null;
    const pending = lists.domains?.filter((domain) => !domain.verified) ?? null;
    const planName = user?.plan ? settings.plan.names[user.plan.name] || user.plan.name : common.loading;

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

                {lists.failed ? (
                    <p className={styles.failed} role="alert">
                        {settings.loadFailed}
                    </p>
                ) : null}

                <SettingsSection title={settings.watch.title}>
                    <WatchSettings watches={lists.watches} onChange={changed} />
                </SettingsSection>

                <SettingsSection title={settings.domains.title}>
                    {verified === null ? <p>{common.loading}</p> : null}
                    {verified?.length === 0 ? <p className={styles.muted}>{settings.domains.empty}</p> : null}
                    {verified?.length ? (
                        <ul className={styles.domains}>
                            {verified.map((domain) => (
                                <li key={domain.id} className={styles.domain}>
                                    <span className={styles.host}>
                                        <Breakable text={domain.hostname} />
                                    </span>
                                    <span className={styles.verified} aria-label={settings.domains.verifiedLabel}>
                                        {settings.domains.verified}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    ) : null}
                    <UnverifiedCache domains={pending} watches={lists.watches} onChange={changed} />
                </SettingsSection>

                <SettingsSection title={settings.plan.title}>
                    <SettingsRow
                        label={settings.plan.plan}
                        value={planName}
                        action={
                            <Link to="/pricing" className={styles.compare}>
                                {settings.plan.compare}
                            </Link>
                        }
                    />
                    <SettingsRow
                        label={settings.plan.scans}
                        value={allowance ? fill(settings.plan.remaining, allowance) : settings.plan.unlimited}
                    />
                </SettingsSection>
            </PageBody>
        </>
    );
}
