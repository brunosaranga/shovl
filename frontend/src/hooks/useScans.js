import { useEffect, useState } from "react";
import { scansApi } from "../lib/api";
import { isFinished, isInProgress } from "../lib/severity";

const POLL_MS = 3000;

// The signed-in user's scans, newest first (GET /api/scans/). Keeps polling while any scan is
// still in progress (running, paused…), so a scan that ends elsewhere doesn't stay "scanning".
// A failed refresh after the first load keeps the list on screen and stops polling.
export function useScanList() {
    const [state, setState] = useState({ loaded: false, scans: [], error: null });

    useEffect(() => {
        let cancelled = false;
        let timer;
        let loadedOnce = false;

        const load = () =>
            scansApi
                .list()
                .then(({ data }) => {
                    if (cancelled) return;
                    const scans = Array.isArray(data) ? data : data?.results || [];
                    loadedOnce = true;
                    setState({ loaded: true, scans, error: null });
                    if (scans.some((scan) => isInProgress(scan.status))) timer = setTimeout(load, POLL_MS);
                })
                .catch((error) => {
                    if (!cancelled && !loadedOnce) setState({ loaded: true, scans: [], error });
                });

        load();
        return () => {
            cancelled = true;
            clearTimeout(timer);
        };
    }, []);

    return { scans: state.scans, loading: !state.loaded, error: state.error };
}

// One scan (GET /api/scans/<id>/). Keeps polling while it is still pending, running or paused.
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
