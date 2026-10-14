import Alert from "../../../ui/Alert/Alert";
import { useContent } from "../../../../hooks/useContent";
import { checksNotRun } from "../../../../lib/severity";
import { fill } from "../../../../lib/text";

// "based on 5 of 6 checks", plus which checks could not run and why.
// Shown whenever a check came back as ERROR. On a real domain that is every scan:
// mass assignment is skipped there (it writes data) and says so in its detail.
export default function CoverageNote({ meta, findings = [], summary = {} }) {
    const { report } = useContent();
    const notRun = checksNotRun(findings);

    const total = meta?.total_checks ?? findings.length;
    const failed = meta?.checks_failed ?? summary.ERROR ?? notRun.length;
    const run = meta?.checks_run ?? Math.max(total - failed, 0);
    const incomplete = String(meta?.risk_score || "").toUpperCase() === "INCOMPLETE";

    if (!failed && !incomplete) return null;

    return (
        <Alert tone={incomplete ? "danger" : "info"}>
            <p>{incomplete ? fill(report.coverage.incomplete, { total }) : fill(report.coverage.partial, { run, total })}</p>
            {notRun.length ? (
                <>
                    <p>{report.coverage.notRunTitle}</p>
                    <ul>
                        {notRun.map((finding, index) => (
                            <li key={`${finding.id}-${index}`}>
                                <strong>{finding.check}</strong>
                                {finding.detail?.[0] ? ` — ${finding.detail[0]}` : ""}
                            </li>
                        ))}
                    </ul>
                </>
            ) : null}
        </Alert>
    );
}
