import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useSound } from "../context/SoundContext";
import { hasAmbiance } from "../routes";

// The hooks that tie lib/sound.js to what's on screen. One-off cues from a click
// (a knob, a refused form) call useSound().play() directly instead.

/** Plays `cue` whenever `trigger` becomes truthy or changes to another truthy value. */
export function useSoundCue(cue, trigger) {
    const { play } = useSound();

    useEffect(() => {
        if (trigger) play(cue);
    }, [cue, trigger, play]);
}

/** Ambiance follows the page: on everywhere except routes marked `ambiance: false`. Used once, in Layout. */
export function useRouteAmbiance() {
    const { pathname } = useLocation();
    const { setAmbiance } = useSound();
    const on = hasAmbiance(pathname);

    useEffect(() => {
        setAmbiance(on);
    }, [on, setAmbiance]);
}

/**
 * The scan page's sound, driven by useScanStream's phase:
 *   running              → the scan track, once (again from the top after "try again")
 *   complete             → scanComplete
 *   failed / error       → scanFailed (the scan couldn't finish, or the connection dropped)
 *   refused              → error (the scan never started: allowance, unverified domain…)
 * Leaving the page fades the scan track out.
 */
export function useScanSounds(phase, enabled = true) {
    const { play, prepareScan, startScan, stopScan } = useSound();

    useEffect(() => {
        if (!enabled) return undefined;
        prepareScan();
        return () => stopScan();
    }, [enabled, prepareScan, stopScan]);

    useEffect(() => {
        if (!enabled) return;
        if (phase === "running") {
            startScan();
        } else if (phase === "complete") {
            stopScan();
            play("scanComplete");
        } else if (phase === "failed" || phase === "error") {
            stopScan();
            play("scanFailed");
        } else if (phase === "refused") {
            play("error");
        }
    }, [enabled, phase, play, startScan, stopScan]);
}

/**
 * A report opened while its scan was still running: play the outcome when it lands.
 * Opening a report that has already finished stays quiet.
 */
export function useScanOutcomeSound(status) {
    const { play } = useSound();
    const previous = useRef(status);

    useEffect(() => {
        const was = previous.current;
        previous.current = status;
        if (was !== "running" && was !== "pending") return;
        if (status === "complete") play("scanComplete");
        else if (status === "failed" || status === "interrupted") play("scanFailed");
    }, [status, play]);
}
