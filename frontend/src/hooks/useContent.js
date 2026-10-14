import { content, defaultLocale } from "../content";

// Returns the copy tree. Usage: const { landing, common } = useContent();
// One language for now; a LocaleContext slots in here when a second one exists.
export function useContent() {
    return content[defaultLocale];
}
