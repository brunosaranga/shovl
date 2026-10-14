import { useEffect, useState } from "react";
import { scansApi } from "../lib/api";
import { isFinished } from "../lib/severity";

const POLL_MS = 3000;

// The signed-in user's scans, newest first (GET /api/scans/).
export function useScanList() {
    const [state, setState] = useState({ loaded: false, scans: [], error: null });

    useEffect(() => {
        let cancelled = false;
        scansApi
            .list()
            .then(({ data }) => {
                if (!cancelled) setState({ loaded: true, scans: Array.isArray(data) ? data : data?.results || [], error: null });
            })
            .catch((error) => {
                if (!cancelled) setState({ loaded: true, scans: [], error });
            });
        return () => {
            cancelled = true;
        };
    }, []);

    return { scans: state.scans, loading: !state.loaded, error: state.error };
}

// One scan (GET /api/scans/<id>/). Keeps polling while it is still pending or running.
export function useScanDetail(scanId) {
    // `id` records which scan the data belongs to, so a new scanId reads as "loading".
    const [state, setState] = useState({ id: null, scan: null, error: null });

    useEffect(() => {
        let cancelled = false;
        let timer;

        const load = () =>
            scansApi
                .detail(scanId)
                .then(({ data }) => {
                    if (cancelled) return;
                    setState({ id: scanId, scan: data, error: null });
                    if (!isFinished(data.status)) timer = setTimeout(load, POLL_MS);
                })
                .catch((error) => {
                    if (!cancelled) setState((previous) => ({ ...previous, id: scanId, error }));
                });

        load();
        return () => {
            cancelled = true;
            clearTimeout(timer);
        };
    }, [scanId]);

    const current = state.id === scanId;
    return {
        scan: current ? state.scan : null,
        loading: !current,
        error: current ? state.error : null,
    };
}
