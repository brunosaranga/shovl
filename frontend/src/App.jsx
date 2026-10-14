import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { SessionProvider } from "./context/SessionContext";
import { ThemeProvider } from "./context/ThemeContext";
import { routerConfig } from "./routes";

const router = createBrowserRouter(routerConfig);

export default function App() {
    return (
        <ThemeProvider>
            <SessionProvider>
                <RouterProvider router={router} />
            </SessionProvider>
        </ThemeProvider>
    );
}
