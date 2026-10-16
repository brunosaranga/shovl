import Knob from "../../../ui/Knob/Knob";
import { useContent } from "../../../../hooks/useContent";
import styles from "./ScanOptions.module.css";

// The three scan-option knobs. `options` = { verbose, generateReport, suggestFix }.
export default function ScanOptions({ options, onChange }) {
    const { landing } = useContent();
    const set = (key) => (value) => onChange({ ...options, [key]: value });

    return (
        <div className={styles.row}>
            <Knob 
            name="verbose" 
            label={landing.options.verbose} 
            active={options.verbose} 
            onChange={set("verbose")} />

            <Knob
                name="generateReport"
                label={landing.options.generateReport}
                active={options.generateReport}
                onChange={set("generateReport")}
            />

            <Knob 
            name="suggestFix" 
            label={landing.options.suggestFix} 
            active={options.suggestFix} 
            onChange={set("suggestFix")} />
        </div>
    );
}
