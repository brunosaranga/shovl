import { useCallback, useState } from "react";
import { scansApi } from "../lib/api";
import { blobErrorBody, filenameFrom, saveBlob } from "../lib/download";

// "download pdf" on the report page. The API builds the PDF from the saved scan, so every
// finished scan has one and downloading it never uses up a scan.
// Returns { download, busy, error }: error is "disabled" | "tooMany" | "notComplete" | "failed"
// (copy in content/en/report.js, pdf.errors), or null.
export function usePdfDownload(scanId) {
    // `scanId` records which scan the state belongs to, so another report starts clean.
    const [state, setState] = useState({ scanId: null, busy: false, error: null });

    const download = useCallback(async () => {
        setState({ scanId, busy: true, error: null });
        try {
            const response = await scansApi.pdf(scanId);
            const name = filenameFrom(response.headers?.["content-disposition"], `xikomu-report-${scanId}.pdf`);
            saveBlob(response.data, name);
            setState({ scanId, busy: false, error: null });
        } catch (error) {
            const status = error.response?.status;
            const { code } = await blobErrorBody(error);
            let reason = "failed";
            if (code === "pdf_disabled") reason = "disabled";
            else if (code === "scan_not_complete") reason = "notComplete";
            else if (status === 429) reason = "tooMany";
            setState({ scanId, busy: false, error: reason });
        }
    }, [scanId]);

    const current = state.scanId === scanId;
    return { download, busy: current && state.busy, error: current ? state.error : null };
}
