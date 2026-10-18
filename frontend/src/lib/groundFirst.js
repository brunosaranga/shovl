// The ground loads first.
//
// On a first visit the ground is what the page is waiting for: the still image (preloaded and
// painted from index.html before the app's JavaScript arrives), then the 2.4 MB walking loop.
// Anything else heavy waits here until the ground has loaded, so it doesn't share the
// connection with it: the sound files (lib/sound.js) start downloading only after that.
//
//   loaded    the walking loop is fully downloaded (it's already playing by then), or the
//             still image has loaded when the loop isn't used (reduced motion, Safari, an
//             error). layout/Ground calls groundLoaded().
//   give up   after GIVE_UP_MS anyway, so a very slow connection doesn't hold the rest back.
//
// The page's text and buttons don't wait: they come with the app itself. On a good connection
// all of this takes a second or two; on a slow one the knob clicks are silent until then.

const GIVE_UP_MS = 12000;

let loaded = false;
let release = () => {};
const gate = new Promise((resolve) => {
    release = resolve;
});

/** The ground has loaded (or given up): let everything else start. Safe to call more than once. */
export function groundLoaded() {
    if (loaded) return;
    loaded = true;
    release();
}

/** Resolves once the ground has loaded. */
export function whenGroundLoaded() {
    return gate;
}

export function isGroundLoaded() {
    return loaded;
}

setTimeout(groundLoaded, GIVE_UP_MS);

// ---- showing: for the entrance (hooks/useEntrance.js) ------------------------------------
// Sooner than "loaded": the walking loop has started playing (it may still be downloading),
// or the still image is up when the loop isn't used. The page fades in after this.
let showing = false;
let reveal = () => {};
const shown = new Promise((resolve) => {
    reveal = resolve;
});

/** The ground is on screen and, where it can, walking. Safe to call more than once. */
export function groundShowing() {
    if (showing) return;
    showing = true;
    reveal();
}

/** Resolves once the ground is showing. */
export function whenGroundShowing() {
    return shown;
}
