import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Landing from './pages/Landing'
import Auth from './pages/Auth'
import Dashboard from  './pages/Dashboard'
import Settings from './pages/Settings'
// import SignIn from './pages/SignIn'
// import Register from './pages/Register'

import ScanRunning from './pages/ScanRunning'
import Report from './pages/Report'

import DomainVerification from './pages/DomainVerification'
// import ProtectedRoute from './components/auth/ProtectedRoute'

// 1. Import the AuthProvider context wrapper
import { AuthProvider } from "./context/AuthContext";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/"                    element={<Landing />} />
          <Route path="/verify"              element={<DomainVerification />} />
          <Route path="/signin"              element={<Auth />} />
          <Route path="/scan/running"  element={<ScanRunning />} />
          <Route path="/dashboard"         element={<Dashboard />} />
          <Route path="/settings"          element={<Settings />} />
          <Route path="/report"   element={<Report />} />
          {/* <Route path="/register"            element={<Register />} /> */}

          {/* Protected Routes - routes only accessed when authenticated */}
          {/* <Route element={<ProtectedRoute />}> */}
            {/* <Route path="/dashboard"         element={<Dashboard />} /> */}
            {/* <Route path="/scan/new"          element={<NewScan />} />
            <Route path="/scan/:id/running"  element={<ScanRunning />} />
            <Route path="/scan/:id/report"   element={<Report />} />
            <Route path="/verify"              element={<DomainVerification />} />
            <Route path="/settings"          element={<Settings />} /> */}
          {/* </Route> */}

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}