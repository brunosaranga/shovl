import { useLayoutEffect, useRef } from "react";
import { fadeIn } from "../lib/entrance";
import { whenGroundShowing } from "../lib/groundFirst";

// The entrance, once per page load: the ground is on its own first, then the rest of the page
// fades in. Moving between pages afterwards doesn't replay it, and visitors who ask for
// reduced motion get the page straight away.
//
//   hold     everything but the ground is hidden (Layout.module.css, data-entrance="hold")
//   release  once the ground is showing (walking, or its still image when the loop isn't
//            used) and has had the screen to itself for MIN_ALONE_MS since the page started
//            loading, or after MAX_WAIT_MS once the app is up, whichever comes first
//   fade     FADE_MS (lib/entrance.js)

const MIN_ALONE_MS = 900; // counted from the start of the page load, the boot ground included
const MAX_WAIT_MS = 1600; // the longest the page waits for the ground once the app is up
const FADE_MS = 800;
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

let played = false;

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, Math.max(0, ms)));

/** Returns the ref for the layout's shell. */
export function useEntrance() {
    const shellRef = useRef(null);

    // A layout effect runs before the first paint, so the page is never seen before the hold.
    useLayoutEffect(() => {
        const shell = shellRef.current;
        if (!shell || played) return undefined;
        if (window.matchMedia?.(REDUCED_MOTION).matches) {
            played = true;
            return undefined;
        }

        let cancelled = false;
        shell.dataset.entrance = "hold";
        const groundReady = whenGroundShowing().then(() => wait(MIN_ALONE_MS - performance.now()));

        Promise.race([groundReady, wait(MAX_WAIT_MS)]).then(() => {
            if (cancelled) return;
            played = true;
            // Same task: the hold comes off and the fade starts before the next paint.
            delete shell.dataset.entrance;
            fadeIn(shell, FADE_MS);
        });

        return () => {
            cancelled = true;
            delete shell.dataset.entrance;
        };
    }, []);

    return shellRef;
}
