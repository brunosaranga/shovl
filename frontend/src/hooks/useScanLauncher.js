import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { useSound } from "../context/SoundContext";
import { describeError } from "../lib/apiErrors";
import { extractHostname, isPracticeTarget, normalizeTargetUrl } from "../lib/targets";
import { useContent } from "./useContent";

// Decides where "dig deeper" goes.
//
//   no URL / not a URL          → shake the input
//   real domain + registered    → /verify (prove ownership first)
//   real domain + guest/nobody  → /signin, register tab (guests can only scan practice targets)
//   practice target + nobody    → needs the consent tick, then creates a guest session
//   practice target + a session → /scan/running
// Every refusal here plays the error cue, so pressing "dig deeper" again replays it.
export function useScanLauncher() {
    const navigate = useNavigate();
    const { status, startGuestSession } = useSession();
    const { play } = useSound();
    const { landing, errors } = useContent();

    const [urlError, setUrlError] = useState(null); // null | "empty" | "invalid"
    const [consentError, setConsentError] = useState(false);
    const [launchError, setLaunchError] = useState(null); // { message, code }
    const [busy, setBusy] = useState(false);

    const flash = (setter, value) => {
        setter(value);
        setTimeout(() => setter(value === true ? false : null), 1500);
    };

    const launch = async ({ url, options, consent }) => {
        setLaunchError(null);

        if (!url?.trim()) {
            play("error");
            flash(setUrlError, "empty");
            return { focus: "url" };
        }
        const target = normalizeTargetUrl(url);
        if (!extractHostname(target)) {
            play("error");
            setUrlError("invalid");
            setLaunchError({ message: landing.invalidUrl });
            return { focus: "url" };
        }

        const pendingScan = {
            url: target,
            verbose: Boolean(options.verbose),
            suggest_fix: Boolean(options.suggestFix),
            generate_report: Boolean(options.generateReport),
        };

        if (!isPracticeTarget(target)) {
            if (status === "registered") {
                navigate("/verify", { state: pendingScan });
            } else {
                navigate("/signin", { state: { mode: "register", notice: "registerForOwnDomain", pendingScan } });
            }
            return {};
        }

        if (status === "anonymous") {
            if (!consent) {
                play("error");
                flash(setConsentError, true);
                return { focus: "consent" };
            }
            setBusy(true);
            try {
                await startGuestSession();
            } catch (error) {
                play("error");
                const described = describeError(error, errors);
                setLaunchError({
                    message: described.code === "too_many_sessions" ? errors.codes.too_many_sessions : described.message,
                    code: described.code,
                });
                return {};
            } finally {
                setBusy(false);
            }
        }

        navigate("/scan/running", { state: pendingScan });
        return {};
    };

    return { launch, urlError, consentError, launchError, busy, clearUrlError: () => setUrlError(null) };
}
