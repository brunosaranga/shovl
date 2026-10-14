import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { SessionProvider } from "./context/SessionContext";
import { routerConfig } from "./routes";

const router = createBrowserRouter(routerConfig);

export default function App() {
    return (
        <SessionProvider>
            <RouterProvider router={router} />
        </SessionProvider>
    );
}
