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
 *   connecting           → the page just opened (or "try again"): every other sound stops at once,
 *                          the scan track plays once from the top
 *   complete             → scanComplete
 *   failed / error       → scanFailed (the scan couldn't finish, or the connection dropped)
 *   refused              → error (the scan never started: allowance, unverified domain…)
 *   stopped              → the scan track stops, no cue (stopped on purpose, or paused too long)
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
        if (phase === "connecting") {
            startScan();
        } else if (phase === "complete") {
            stopScan();
            play("scanComplete");
        } else if (phase === "failed" || phase === "error") {
            stopScan();
            play("scanFailed");
        } else if (phase === "refused") {
            stopScan();
            play("error");
        } else if (phase === "stopped") {
            stopScan();
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
        if (was !== "running" && was !== "pending" && was !== "paused") return;
        if (status === "complete") play("scanComplete");
        else if (status === "failed" || status === "interrupted") play("scanFailed");
    }, [status, play]);
}
