import { useState } from "react";
import Pagination from "../../../ui/Pagination/Pagination";
import ScanRow from "./ScanRow";
import { useContent } from "../../../../hooks/useContent";
import styles from "./ScanList.module.css";

const PAGE_SIZE = 8;

// "your scans": newest first, one row open at a time, paged on the client.
export default function ScanList({ scans, loading, error }) {
    const { dashboard } = useContent();
    const [expandedId, setExpandedId] = useState(null);
    const [page, setPage] = useState(1);

    const pageCount = Math.max(1, Math.ceil(scans.length / PAGE_SIZE));
    const current = Math.min(page, pageCount);
    const visible = scans.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

    return (
        <div className={styles.list}>
            <h2 className={styles.title}>{dashboard.listTitle}</h2>

            {loading ? <p className="meta-line">{dashboard.loading}</p> : null}
            {!loading && error ? <p className="meta-line">{dashboard.loadFailed}</p> : null}
            {!loading && !error && !scans.length ? <p className="meta-line">{dashboard.empty}</p> : null}

            {visible.map((scan) => (
                <ScanRow
                    key={scan.id}
                    scan={scan}
                    expanded={expandedId === scan.id}
                    onToggle={() => setExpandedId(expandedId === scan.id ? null : scan.id)}
                />
            ))}

            <Pagination page={current} pageCount={pageCount} onChange={setPage} />
        </div>
    );
}
