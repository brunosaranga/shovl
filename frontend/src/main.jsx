// import { StrictMode } from 'react'
// import { createRoot } from 'react-dom/client'
// import './index.css'
// import App from './App.jsx'
// import { AuthProvider } from "./context/AuthContext";

// createRoot(document.getElementById('root')).render(
//   <AuthProvider>
//     <App />
//   </AuthProvider>,
// )

import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import './styles/global.css'
// import { AuthProvider } from "./context/AuthContext";

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
