import { useSound } from "../../../context/SoundContext";
import { useContent } from "../../../hooks/useContent";
import styles from "./SoundToggle.module.css";

// Square button in the navbar, left of the theme toggle: a speaker with sound waves while
// sound is on, a crossed-out speaker while muted. Muting pauses the ambiance and the scan
// track where they are and silences every cue; the choice is remembered (lib/sound.js).
export default function SoundToggle({ className = "" }) {
    const { muted, toggleMuted } = useSound();
    const { common } = useContent();
    const label = muted ? common.sound.unmute : common.sound.mute;

    return (
        <button
            type="button"
            className={[styles.toggle, className].filter(Boolean).join(" ")}
            onClick={toggleMuted}
            aria-label={label}
            title={label}
        >
            <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.icon}>
                <path fill="currentColor" d="M2 8.5h4.5L12 3.5v17l-5.5-5H2z" />
                <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="square">
                    {muted ? (
                        <path d="M16 9l5.5 6M21.5 9L16 15" />
                    ) : (
                        <path d="M15.5 9.2a3.6 3.6 0 0 1 0 5.6M18.5 6a8 8 0 0 1 0 12" />
                    )}
                </g>
            </svg>
        </button>
    );
}
