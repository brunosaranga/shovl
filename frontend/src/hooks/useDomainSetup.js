import { useEffect, useState } from "react";
import { domainsApi } from "../lib/api";
import { describeError } from "../lib/apiErrors";
import { useContent } from "./useContent";

// Makes sure a Domain record exists for `hostname` and returns it (with its real,
// server-generated verification token).
//
// Looks in the list first and only adds when missing. If the add fails anyway
// (another tab added it first, or the backend's duplicate check misfires), it
// looks again before giving up.
export function useDomainSetup(hostname) {
    const { errors } = useContent();
    const [domain, setDomain] = useState(null);
    const [loading, setLoading] = useState(Boolean(hostname));
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!hostname) return undefined;
        let cancelled = false;

        const find = async () => {
            const { data } = await domainsApi.list();
            return (Array.isArray(data) ? data : []).find((item) => item.hostname === hostname) || null;
        };

        const ensure = async () => {
            setLoading(true);
            setError(null);
            try {
                let found = await find();
                if (!found) {
                    try {
                        found = (await domainsApi.add(hostname)).data;
                    } catch (addError) {
                        found = await find();
                        if (!found) throw addError;
                    }
                }
                if (!cancelled) setDomain(found);
            } catch (err) {
                if (!cancelled) setError(describeError(err, errors).message);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        // Next tick, so React's development double-mount doesn't add the domain twice.
        const timer = setTimeout(ensure, 0);
        return () => {
            cancelled = true;
            clearTimeout(timer);
        };
    }, [hostname, errors]);

    return { domain, loading, error };
}
