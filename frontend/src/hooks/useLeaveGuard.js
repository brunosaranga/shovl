import { useCallback, useEffect, useRef } from "react";
import { useBlocker } from "react-router-dom";

// While `active`, leaving the page asks first:
//   - in-app navigation is held by the router until the user answers (blocker.state === "blocked")
//   - closing or reloading the tab shows the browser's own warning
// allowNextLeave() lets one deliberate navigation through (e.g. the stop button).
export function useLeaveGuard(active) {
    const allowRef = useRef(false);

    const blocker = useBlocker(
        useCallback(
            ({ currentLocation, nextLocation }) =>
                active && !allowRef.current && currentLocation.pathname !== nextLocation.pathname,
            [active]
        )
    );

    useEffect(() => {
        if (!active) return undefined;
        const onBeforeUnload = (event) => {
            event.preventDefault();
            event.returnValue = "";
        };
        window.addEventListener("beforeunload", onBeforeUnload);
        return () => window.removeEventListener("beforeunload", onBeforeUnload);
    }, [active]);

    const allowNextLeave = useCallback(() => {
        allowRef.current = true;
    }, []);

    return { blocker, allowNextLeave };
}
