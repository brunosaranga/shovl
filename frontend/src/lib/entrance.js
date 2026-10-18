// The page's entrance: everything but the ground fades in (hooks/useEntrance.js decides when).
//
// Fading a whole page by its opacity would change what sits in front of the ground while it
// fades: opacity below 1 turns an element into its own layer, and everything inside it would
// then be drawn behind the ground (the landing's "dig deeper" button and wordmark sit in front
// of it with their own z-index, the shovel sits behind it). So the fade goes onto the smallest
// pieces that can take it without changing that order: pieces that already are their own
// layer (the navbar, the footer, a page whose content sits over the ground), and pieces with
// nothing inside that has a z-index of its own.

function hasOwnLayer(style) {
    return style.zIndex !== "auto" || style.transform !== "none" || Number(style.opacity) < 1 || style.filter !== "none";
}

function hasLayeredInside(element) {
    for (const child of element.querySelectorAll("*")) {
        if (getComputedStyle(child).zIndex !== "auto") return true;
    }
    return false;
}

/** The pieces of the shell to fade, the ground left out (it carries data-ground). */
export function fadeTargets(shell) {
    const targets = [];
    const visit = (element) => {
        if (element.hasAttribute("data-ground")) return;
        const style = getComputedStyle(element);
        if (style.display === "none") return;
        if (hasOwnLayer(style) || !hasLayeredInside(element)) {
            targets.push(element);
            return;
        }
        Array.from(element.children).forEach(visit);
    };
    Array.from(shell.children).forEach(visit);
    return targets;
}

/** Fades the shell's pieces in from nothing to how they normally look. */
export function fadeIn(shell, duration) {
    fadeTargets(shell).forEach((element) => {
        if (typeof element.animate !== "function") return;
        const opacity = getComputedStyle(element).opacity;
        element.animate([{ opacity: 0 }, { opacity }], { duration, easing: "cubic-bezier(0.25, 0, 0.25, 1)" });
    });
}
