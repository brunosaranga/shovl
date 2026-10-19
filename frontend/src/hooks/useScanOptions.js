import { useState } from "react";

// The landing page's three knobs. What the visitor picks is remembered while they move around
// the app (to a scan, a report, the dashboard and back), so the start page keeps their choice.
// Kept in memory only, on purpose: a refresh, a new tab or a new visit starts from DEFAULTS.
export const DEFAULTS = { verbose: false, generateReport: true, suggestFix: false };

let remembered = DEFAULTS;

/** [options, setOptions], like useState, but the choice outlives the page. */
export function useScanOptions() {
    const [options, setOptions] = useState(remembered);

    const set = (next) => {
        remembered = { ...next };
        setOptions(remembered);
    };

    return [options, set];
}
