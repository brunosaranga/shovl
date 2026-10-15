import { createContext, useContext, useEffect, useMemo, useSyncExternalStore } from "react";
import { sound } from "../lib/sound";

// Sound on or muted, plus the calls pages and hooks use to drive lib/sound.js.
// The provider also installs the listeners that start sound on the visitor's first
// click, tap or key press (browsers keep pages silent until then).
const SoundContext = createContext(null);

export function SoundProvider({ children }) {
    const muted = useSyncExternalStore(sound.subscribe, sound.isMuted);

    useEffect(() => sound.init(), []);

    const value = useMemo(
        () => ({
            muted,
            toggleMuted: sound.toggleMuted,
            setMuted: sound.setMuted,
            play: sound.play,
            setAmbiance: sound.setAmbiance,
            prepareScan: sound.prepareScan,
            startScan: sound.startScan,
            stopScan: sound.stopScan,
        }),
        [muted]
    );

    return <SoundContext.Provider value={value}>{children}</SoundContext.Provider>;
}

export function useSound() {
    const ctx = useContext(SoundContext);
    if (!ctx) {
        throw new Error("useSound must be used inside <SoundProvider>");
    }
    return ctx;
}
