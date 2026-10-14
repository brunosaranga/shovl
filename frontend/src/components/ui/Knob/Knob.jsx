import verboseOn from "../../../assets/knobs/verboseKnobOn.svg";
import verboseOff from "../../../assets/knobs/verboseKnobOff.svg";
import reportOn from "../../../assets/knobs/genReportKnobOn.svg";
import reportOff from "../../../assets/knobs/genReportKnobOff.svg";
import fixOn from "../../../assets/knobs/suggestFixKnobOn.svg";
import fixOff from "../../../assets/knobs/suggestFixKnobOff.svg";
import styles from "./Knob.module.css";

// The Figma knob artwork and how far each one turns.
const KNOBS = {
    verbose: { on: verboseOn, off: verboseOff, onAngle: "0deg", offAngle: "-50deg" },
    generateReport: { on: reportOn, off: reportOff, onAngle: "0deg", offAngle: "-45deg" },
    suggestFix: { on: fixOn, off: fixOff, onAngle: "15deg", offAngle: "-35deg" },
};

// A toggle drawn as a knob. `name` picks the artwork; `label` is the visible text.
export default function Knob({ name, label, active, onChange }) {
    const knob = KNOBS[name] || KNOBS.verbose;
    const angle = active ? knob.onAngle : knob.offAngle;

    return (
        <button type="button" className={styles.knob} aria-pressed={active} onClick={() => onChange(!active)}>
            <img className={styles.dial} src={active ? knob.on : knob.off} alt="" style={{ "--knob-angle": angle }} />
            <span className={styles.label}>{label}</span>
        </button>
    );
}
