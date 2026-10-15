import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { SessionProvider } from "./context/SessionContext";
import { SoundProvider } from "./context/SoundContext";
import { ThemeProvider } from "./context/ThemeContext";
import { routerConfig } from "./routes";

const router = createBrowserRouter(routerConfig);

export default function App() {
    return (
        <ThemeProvider>
            <SoundProvider>
                <SessionProvider>
                    <RouterProvider router={router} />
                </SessionProvider>
            </SoundProvider>
        </ThemeProvider>
    );
}
