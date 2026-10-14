import { createContext, useContext } from "react";

// The DOM node in the navbar's middle slot. Layout provides it; pages fill it
// through <NavCenter> (a portal), so the shell never needs to know what a page shows there.
const NavSlotContext = createContext(null);

export const NavSlotProvider = NavSlotContext.Provider;

export function useNavSlot() {
    return useContext(NavSlotContext);
}
