import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider } from "./context/AuthContext"
import ProtectedRoute from './components/auth/ProtectedRoute'

import Landing from './pages/Landing'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import ScanRunning from './pages/ScanRunning'
import Report from './pages/Report'
import DomainVerification from './pages/DomainVerification'

export default function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    {/* Public */}
                    <Route path="/"       element={<Landing />} />
                    <Route path="/signin" element={<Auth />} />

                    {/* Protected */}
                    <Route element={<ProtectedRoute />}>
                        <Route path="/verify"                  element={<DomainVerification />} />
                        <Route path="/dashboard"               element={<Dashboard />} />
                        <Route path="/settings"                element={<Settings />} />
                        <Route path="/scan/:scanId/running"    element={<ScanRunning />} />
                        <Route path="/scan/:scanId/report"     element={<Report />} />
                    </Route>

                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    )
}