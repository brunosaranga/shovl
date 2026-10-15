import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./styles/tokens.css";
import "./styles/reset.css";
import "./styles/base.css";
import "./styles/utilities.css";

import App from "./App";
import { wakeApi } from "./lib/api";

// Start waking the API (free plan) before anyone clicks anything.
wakeApi();

createRoot(document.getElementById("root")).render(
    <StrictMode>
        <App />
    </StrictMode>
);
