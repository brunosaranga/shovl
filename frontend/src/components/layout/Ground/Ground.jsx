import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import ground from "../../../assets/images/ground.webp";
import groundLoop from "../../../assets/videos/ground-loop.webm";
import { useMediaQuery } from "../../../hooks/useMediaQuery";
import { groundLoaded, groundShowing } from "../../../lib/groundFirst";
import { isGroundStill } from "../../../routes";
import styles from "./Ground.module.css";

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

// Safari, and every browser on an iPhone or iPad (they all run Apple's WebKit), plays the WebM
// but drops its transparency, so it would keep the still image. Apple's browsers get the same
// loop as HEVC with alpha instead, once assets/videos/ground-loop.mp4 exists. Make it on a Mac
// from the WebM (Homebrew's ffmpeg has Apple's encoder):
//
//   ffmpeg -c:v libvpx-vp9 -i ground-loop.webm -c:v hevc_videotoolbox -allow_sw 1 \
//       -alpha_quality 0.75 -pix_fmt bgra -tag:v hvc1 -b:v 1M -an -movflags +faststart \
//       ground-loop.mp4
//
// (libvpx-vp9 first, as the decoder: ffmpeg's own VP9 decoder drops the alpha; hvc1, or Safari
// won't play it.) Until the file is there, import.meta.glob finds nothing and Apple's browsers
// keep the still image, as before. Every other browser keeps the WebM: Chrome on a Mac can play
// HEVC too, but not its transparency. The sky check below still guards both.
const HEVC_LOOP = Object.values(
    import.meta.glob("../../../assets/videos/ground-loop.mp4", { eager: true, query: "?url", import: "default" })
)[0];

function pickLoop() {
    const apple = typeof navigator !== "undefined" && navigator.vendor === "Apple Computer, Inc.";
    if (!apple || !HEVC_LOOP) return groundLoop;
    return document.createElement("video").canPlayType('video/mp4; codecs="hvc1"') ? HEVC_LOOP : groundLoop;
}

const LOOP = pickLoop();

// Walking speed. 1 = the speed the video was made at (one loop every 22 s). Small changes
// (0.8 to 1.2) are fine; for a big change, re-render the video so the motion stays smooth.
const WALK_RATE = 1;
// How long it takes to come to a halt, or to get going again.
const GLIDE_MS = 1600;
// The slowest rate browsers accept; below it the video is paused instead.
const MIN_RATE = 0.0625;

function setRate(video, rate) {
    try {
        video.playbackRate = rate;
    } catch {
        // outside this browser's range: keep the last rate
    }
}

// Glides the playback rate to `target` (0 = halt) and pauses at the end of a halt.
// A paused video keeps its frame, so walking resumes from the same spot.
// Returns a cancel function, so a new target can take over mid-glide.
function glideTo(video, target) {
    const from = video.paused ? 0 : video.playbackRate;
    if (target > 0 && video.paused) {
        setRate(video, MIN_RATE);
        // refused (low-power mode, autoplay off): the still image stays
        video.play().catch(() => {});
    }
    const start = performance.now();
    let frame = 0;

    const step = (now) => {
        const t = Math.min(1, (now - start) / GLIDE_MS);
        const eased = t * t * (3 - 2 * t);
        const rate = from + (target - from) * eased;
        if (t === 1 && target === 0) {
            video.pause();
            return;
        }
        setRate(video, Math.max(MIN_RATE, rate));
        if (t < 1) frame = requestAnimationFrame(step);
    };

    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
}

// True once the whole loop is downloaded, or the browser has stopped fetching it with enough
// to play (it "suspends" the download): from then on nothing else competes with it.
function isLoaded(video, eventType) {
    const { buffered, duration } = video;
    if (buffered.length && duration && buffered.end(buffered.length - 1) >= duration - 0.5) return true;
    return eventType === "suspend" && video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA;
}

// True when the video's sky came through transparent. Safari plays WebM but drops the
// transparency (the sky turns solid): without the HEVC loop it keeps the still image.
function hasTransparentSky(video) {
    try {
        const canvas = document.createElement("canvas");
        canvas.width = 8;
        canvas.height = 8;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        // the top-left corner of every frame is sky
        ctx.drawImage(video, 0, 0, 64, 64, 0, 0, 8, 8);
        const { data } = ctx.getImageData(0, 0, 8, 8);
        return data[3] < 16;
    } catch {
        return false;
    }
}

// The low-poly ground along the bottom of every page. The still image paints first; the
// walking-through-the-dunes loop fades in over it once it plays with a transparent sky.
// On pages marked `ground: "still"` in routes.jsx (the scan page) the walk slows to a halt,
// and it picks up again from the same spot on the next page.
// Visitors who ask for reduced motion, and browsers that can't show the transparency
// (or won't autoplay: an iPhone in Low Power Mode), keep the still image. Apple's browsers
// play the HEVC version of the loop when there is one (HEVC_LOOP above).
//
// The ground loads first (lib/groundFirst.js): index.html paints the still image before the
// app arrives (#ground-boot), this component takes over from it, and tells the rest of the
// app when the ground is showing (the page's entrance fades in then: hooks/useEntrance.js)
// and when it has loaded (the sound files start downloading then).
export default function Ground() {
    const { pathname } = useLocation();
    const still = isGroundStill(pathname);
    const reduceMotion = useMediaQuery(REDUCED_MOTION_QUERY);
    const videoRef = useRef(null);
    // pending → playing, or pending → unsupported (the video is then removed)
    const [status, setStatus] = useState("pending");

    const showVideo = !reduceMotion && status !== "unsupported";

    // Playback is started (and slowed, and stopped) by hand rather than with autoPlay.
    // React sets `muted` as a property, so set it here before the first play().
    useEffect(() => {
        const video = videoRef.current;
        if (!video) return undefined;
        video.muted = true;
        return glideTo(video, still ? 0 : WALK_RATE);
    }, [still, showVideo]);

    // index.html's boot ground has done its job once this one is on the page.
    useEffect(() => {
        document.getElementById("ground-boot")?.remove();
    }, []);

    // Without the loop (reduced motion, Safari, an error) the still image is the whole ground:
    // it has loaded when the image has. With the loop, onLoadProgress says when.
    useEffect(() => {
        if (showVideo) return undefined;
        const done = () => {
            groundShowing();
            groundLoaded();
        };
        const image = new Image();
        image.onload = done;
        image.onerror = done;
        image.src = ground;
        return () => {
            image.onload = null;
            image.onerror = null;
        };
    }, [showVideo]);

    const onLoadProgress = (event) => {
        if (isLoaded(event.currentTarget, event.type)) groundLoaded();
    };

    const onPlaying = (event) => {
        if (status !== "pending") return;
        const transparent = hasTransparentSky(event.currentTarget);
        setStatus(transparent ? "playing" : "unsupported");
        if (transparent) groundShowing(); // otherwise the still image says so (above)
    };

    // which layer shows: the video once it's proven itself (even while halted), else the image
    const layer = showVideo && status === "playing" ? "video" : "image";

    return (
        <div className={styles.ground} data-layer={layer} data-ground="" aria-hidden="true">
            <div className={styles.still} style={{ backgroundImage: `url(${ground})` }} />
            {showVideo && (
                <video
                    ref={videoRef}
                    className={styles.video}
                    src={LOOP}
                    muted
                    loop
                    playsInline
                    preload="auto"
                    disablePictureInPicture
                    tabIndex={-1}
                    onPlaying={onPlaying}
                    onProgress={onLoadProgress}
                    onSuspend={onLoadProgress}
                    onCanPlayThrough={onLoadProgress}
                    onError={() => setStatus("unsupported")}
                />
            )}
        </div>
    );
}
