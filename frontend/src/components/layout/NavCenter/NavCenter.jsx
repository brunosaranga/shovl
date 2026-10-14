import { createPortal } from "react-dom";
import { useNavSlot } from "../../../context/NavSlotContext";

// Renders its children in the navbar's middle slot. A page title on most pages,
// the URL input on the landing page (desktop).
export default function NavCenter({ children }) {
    const slot = useNavSlot();
    return slot ? createPortal(children, slot) : null;
}
