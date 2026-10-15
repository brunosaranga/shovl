// The sound layer: the ambiance loop, the scan track, and short cues.
// Plain JavaScript, no React: components reach it through context/SoundContext.
//
//   ambiance   loops on every page except the ones routes.jsx marks `ambiance: false`
//              (verify, scan running). Streamed by an <audio> element because the file is
//              large; it pauses while the tab is hidden.
//   scan       plays once, from the top, each time a scan starts streaming.
//   cues       error, scanComplete, scanFailed, knob: one-shots, decoded once and reused,
//              so they start instantly and can overlap.
//
// Browsers block sound until the visitor clicks, taps or presses a key on the page, so
// nothing plays before that; the first gesture starts whatever the page should be playing.
// Muting pauses the ambiance and the scan track where they are (unmuting resumes them),
// silences cues, and is remembered in localStorage (shovl.sound). While muted, nothing is
// downloaded.
//
// Everything plays through one AudioContext: fades work everywhere (iOS ignores
// <audio>.volume), and a running context can start the scan track without a new gesture.
// The files are served from the same origin as the app. From another origin (a CDN) they
// would need CORS headers and crossOrigin="anonymous" on the <audio> element.
import ambianceUrl from "../assets/sounds/shovl_sound_fx_ambiance.mp3";
import scanRunningUrl from "../assets/sounds/shovl_sound_fx_scan_running.mp3";
import errorUrl from "../assets/sounds/shovl_sound_fx_error.mp3";
import scanCompleteUrl from "../assets/sounds/shovl_sound_fx_scan_complete_success.mp3";
import scanFailedUrl from "../assets/sounds/shovl_sound_fx_scan_failed.mp3";
import knobUrl from "../assets/sounds/shovl_sound_fx_knob_switch.mp3";

const STORAGE_KEY = "shovl.sound"; // "on" | "muted"

// Playback level of each sound, 0 to 1. The files are already balanced against each other.
const LEVELS = {
    ambiance: 1,
    scan: 1,
    error: 1,
    scanComplete: 1,
    scanFailed: 1,
    knob: 1,
};

const CUE_URLS = {
    error: errorUrl,
    scanComplete: scanCompleteUrl,
    scanFailed: scanFailedUrl,
    knob: knobUrl,
};

// Fade lengths, in seconds.
const FADE = {
    in: 1.5, // ambiance coming back, the scan track resuming after a mute
    out: 0.6, // leaving a page with ambiance, the scan ending
    mute: 0.12, // the mute button: quick, but without a click
    start: 0.02, // the scan track starting from the top: keeps its attack
};

// The same cue asked for twice within this window plays once (React's development
// double-mount, or two parts of a page reporting the same failure).
const CUE_DEBOUNCE_MS = 150;

const GESTURES = ["click", "keydown", "touchend"];
const AudioContextClass = window.AudioContext || window.webkitAudioContext || null;
const OfflineContextClass = window.OfflineAudioContext || window.webkitOfflineAudioContext || null;

const state = {
    muted: readMuted(),
    interacted: false, // a click, tap or key press has happened on the page
    ambianceWanted: false, // the current page plays the ambiance
    scanWanted: false, // a scan is running and its track hasn't played to the end
    hidden: document.visibilityState === "hidden",
};

const listeners = new Set();
const decoded = new Map(); // url → AudioBuffer
const loading = new Map(); // url → Promise<AudioBuffer | null>
const lastCue = {};
const ringing = new Set(); // cues, and scan tracks fading out: what the scan page cuts on arrival

let ctx = null;
let decoder = null;
let installs = 0;

const ambiance = { el: null, gain: null, target: "paused", pauseTimer: null };
const scan = { voice: null, offset: 0 }; // voice: { source, gain, startedAt }

// ---- preference ----------------------------------------------------------
function readMuted() {
    try {
        return localStorage.getItem(STORAGE_KEY) === "muted";
    } catch {
        return false;
    }
}

function writeMuted(muted) {
    try {
        localStorage.setItem(STORAGE_KEY, muted ? "muted" : "on");
    } catch {
        // storage unavailable (private mode): the choice still holds for this visit
    }
}

// ---- audio context ---------------------------------------------------------
// Created or woken inside a gesture: that's the only place browsers let it start.
function wake() {
    if (!AudioContextClass) return null;
    if (!ctx) {
        try {
            ctx = new AudioContextClass();
        } catch {
            return null;
        }
    }
    if (ctx.state !== "running") ctx.resume().catch(() => {});
    return ctx;
}

// Not running yet, a sound is only worth trying inside a gesture, which can start it.
function canStartNow() {
    if (ctx?.state === "running") return true;
    const activation = navigator.userActivation;
    return !activation || activation.isActive;
}

function setLevel(gain, value) {
    const param = gain.gain;
    param.cancelScheduledValues(ctx.currentTime);
    param.setValueAtTime(value, ctx.currentTime);
}

function ramp(gain, value, seconds) {
    const param = gain.gain;
    const now = ctx.currentTime;
    param.cancelScheduledValues(now);
    param.setValueAtTime(param.value, now);
    param.linearRampToValueAtTime(value, now + seconds);
}

// ---- decoded files (cues and the scan track) -----------------------------------
// Decoded with an OfflineAudioContext, so files can be ready before the first gesture
// without opening a real context (which browsers warn about).
function decode(data) {
    if (ctx) return ctx.decodeAudioData(data);
    if (!decoder) decoder = new OfflineContextClass(2, 1, 48000);
    return decoder.decodeAudioData(data);
}

function load(url) {
    if (decoded.has(url)) return Promise.resolve(decoded.get(url));
    if (!loading.has(url)) {
        const promise = fetch(url)
            .then((response) => {
                if (!response.ok) throw new Error(`sound ${response.status}`);
                return response.arrayBuffer();
            })
            .then(decode)
            .then((buffer) => {
                decoded.set(url, buffer);
                return buffer;
            })
            .catch(() => null) // missing file or unsupported format: that sound stays silent
            .finally(() => loading.delete(url));
        loading.set(url, promise);
    }
    return loading.get(url);
}

function preloadCues() {
    if (!AudioContextClass || !OfflineContextClass) return;
    Object.values(CUE_URLS).forEach(load);
}

// ---- ambiance (streamed <audio>, looped) ---------------------------------------
function ambianceElement() {
    if (ambiance.el) return ambiance.el;
    const el = new Audio();
    el.src = ambianceUrl;
    el.loop = true;
    el.preload = "auto";
    const gain = ctx.createGain();
    gain.gain.value = 0;
    ctx.createMediaElementSource(el).connect(gain).connect(ctx.destination);
    ambiance.el = el;
    ambiance.gain = gain;
    return el;
}

function startAmbiance() {
    const el = ambianceElement();
    clearTimeout(ambiance.pauseTimer);
    const resuming = ambiance.target !== "playing";
    ambiance.target = "playing";

    if (el.paused) {
        // Fade in once playback has really started (it may wait for data, or for a gesture).
        setLevel(ambiance.gain, 0);
        el.play()
            .then(() => {
                if (ambiance.target === "playing") ramp(ambiance.gain, LEVELS.ambiance, FADE.in);
            })
            .catch(() => {
                // blocked until a gesture, or paused again before it started: the next sync retries
            });
    } else if (resuming) {
        ramp(ambiance.gain, LEVELS.ambiance, FADE.in);
    }
}

function stopAmbiance(fade) {
    const el = ambiance.el;
    if (!el) return;
    if (fade <= 0) {
        // Hard cut, even in the middle of a fade-out.
        ambiance.target = "paused";
        clearTimeout(ambiance.pauseTimer);
        setLevel(ambiance.gain, 0);
        if (!el.paused) el.pause();
        return;
    }
    if (ambiance.target === "paused") return;
    ambiance.target = "paused";
    ramp(ambiance.gain, 0, fade);
    clearTimeout(ambiance.pauseTimer);
    ambiance.pauseTimer = setTimeout(() => {
        if (ambiance.target === "paused") el.pause();
    }, fade * 1000 + 50);
}

// ---- scan track (decoded, plays once) ------------------------------------------
function startScanVoice() {
    if (scan.voice) return;
    const buffer = decoded.get(scanRunningUrl);
    if (!buffer) {
        // Still downloading: start when it lands, if the scan still wants it.
        load(scanRunningUrl).then((loaded) => loaded && sync());
        return;
    }
    if (scan.offset >= buffer.duration) {
        state.scanWanted = false;
        scan.offset = 0;
        return;
    }

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    source.connect(gain).connect(ctx.destination);

    const voice = { source, gain, startedAt: ctx.currentTime - scan.offset };
    source.onended = () => {
        if (scan.voice !== voice) return; // stopped on purpose
        // Played to the end: once per scan.
        scan.voice = null;
        scan.offset = 0;
        state.scanWanted = false;
    };
    source.start(0, scan.offset);
    ramp(gain, LEVELS.scan, scan.offset > 0 ? FADE.in : FADE.start);
    scan.voice = voice;
}

function stopScanVoice(fade) {
    const voice = scan.voice;
    if (!voice) return;
    scan.voice = null;
    scan.offset = ctx.currentTime - voice.startedAt; // where an unmute picks it up again
    ramp(voice.gain, 0, fade);
    voice.source.stop(ctx.currentTime + fade);
    voice.source.onended = () => ringing.delete(voice.source);
    ringing.add(voice.source);
}

// ---- what should be playing right now ----------------------------------------------
function sync(fade = FADE.out) {
    if (!state.interacted || !ctx) return;
    const audible = !state.muted;

    if (audible && state.ambianceWanted && !state.hidden && !state.scanWanted) startAmbiance();
    else stopAmbiance(fade);

    if (audible && state.scanWanted) startScanVoice();
    else stopScanVoice(fade);
}

function onGesture() {
    if (!wake()) return;
    state.interacted = true;
    if (!state.muted) load(scanRunningUrl); // ready before the visitor reaches the scan page
    sync();
}

function onVisibility() {
    state.hidden = document.visibilityState === "hidden";
    if (!state.hidden && ctx && ctx.state !== "running") ctx.resume().catch(() => {});
    sync();
}

function notify() {
    listeners.forEach((listener) => listener());
}

// ---- public API ----------------------------------------------------------------------
/** Installs the gesture and visibility listeners. Returns the uninstall function. */
function init() {
    installs += 1;
    if (installs === 1) {
        // Bubble phase on document: React's own click handlers (the mute button) run first.
        GESTURES.forEach((type) => document.addEventListener(type, onGesture));
        document.addEventListener("visibilitychange", onVisibility);
        if (!state.muted) preloadCues();
    }
    return () => {
        installs -= 1;
        if (installs > 0) return;
        GESTURES.forEach((type) => document.removeEventListener(type, onGesture));
        document.removeEventListener("visibilitychange", onVisibility);
    };
}

/** One-shot cue: "error" | "scanComplete" | "scanFailed" | "knob". */
function play(name) {
    const url = CUE_URLS[name];
    if (!url || state.muted || !canStartNow()) return;

    const now = Date.now();
    if (now - (lastCue[name] || 0) < CUE_DEBOUNCE_MS) return;
    lastCue[name] = now;

    const context = wake();
    const buffer = decoded.get(url);
    if (!context) return;
    if (!buffer) {
        load(url); // not downloaded yet: skipped rather than played late
        return;
    }

    const source = context.createBufferSource();
    source.buffer = buffer;
    const gain = context.createGain();
    gain.gain.value = LEVELS[name] ?? 1;
    source.connect(gain).connect(context.destination);
    source.onended = () => ringing.delete(source);
    ringing.add(source);
    source.start();
}

function stopRinging() {
    ringing.forEach((source) => {
        try {
            source.stop();
        } catch {
            // already stopped
        }
    });
    ringing.clear();
}

/** The current page plays the ambiance loop (true) or is quiet (false, cut with no fade). */
function setAmbiance(on) {
    state.ambianceWanted = Boolean(on);
    sync(on ? FADE.out : 0);
}

/** The scan page opened: fetch the scan track so it's ready when the scan starts. */
function prepareScan() {
    if (!state.muted && AudioContextClass && OfflineContextClass) load(scanRunningUrl);
}

/** The scan page opened (or "try again"): cut every other sound, play the scan track once from the top. */
function startScan() {
    if (ctx) {
        stopRinging();
        stopAmbiance(0);
        stopScanVoice(0);
    }
    scan.offset = 0;
    state.scanWanted = true;
    sync();
}

/** The scan ended, or the page closed: fade the scan track out. */
function stopScan() {
    state.scanWanted = false;
    if (ctx) stopScanVoice(FADE.out);
    scan.offset = 0;
}

function setMuted(muted) {
    const next = Boolean(muted);
    if (state.muted === next) return;
    state.muted = next;
    writeMuted(next);
    if (!next) preloadCues();
    sync(FADE.mute);
    notify();
}

function subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

export const sound = {
    init,
    play,
    setAmbiance,
    prepareScan,
    startScan,
    stopScan,
    isMuted: () => state.muted,
    setMuted,
    toggleMuted: () => setMuted(!state.muted),
    subscribe,
};

// Development only: when this file is edited, reload the page instead of hot-swapping the
// module. A hot swap would leave the old copy's audio playing with nothing to stop it,
// while the new copy stays silent.
if (import.meta.hot) {
    import.meta.hot.accept(() => window.location.reload());
}
