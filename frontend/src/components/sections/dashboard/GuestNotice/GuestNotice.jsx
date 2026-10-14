import Alert from "../../../ui/Alert/Alert";
import Button from "../../../ui/Button/Button";
import { useContent } from "../../../../hooks/useContent";

// For guests: how long their scans are kept, and how to keep them.
export default function GuestNotice() {
    const { dashboard } = useContent();
    return (
        <Alert
            tone="accent"
            title={dashboard.guest.title}
            actions={
                <Button to="/signin" state={{ mode: "register" }}>
                    {dashboard.guest.cta}
                </Button>
            }
        >
            <p>{dashboard.guest.text}</p>
            <p>{dashboard.guest.counting}</p>
        </Alert>
    );
}
