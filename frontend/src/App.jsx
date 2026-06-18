import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Landing from './pages/Landing'
import Auth from './pages/Auth'
// import SignIn from './pages/SignIn'
// import Register from './pages/Register'
// import Dashboard from  './pages/Dashboard'
// import NewScan from './pages/NewScan'
// import ScanRunning from './pages/ScanRunning'
// import Report from './pages/Report'
// import Settings from './pages/Settings'
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
          {/* <Route path="/register"            element={<Register />} /> */}

          {/* Protected Routes */}
          {/* <Route element={<ProtectedRoute />}>
            <Route path="/dashboard"         element={<Dashboard />} />
            <Route path="/scan/new"          element={<NewScan />} />
            <Route path="/scan/:id/running"  element={<ScanRunning />} />
            <Route path="/scan/:id/report"   element={<Report />} />
            <Route path="/verify"              element={<DomainVerification />} />
            <Route path="/settings"          element={<Settings />} />
          </Route> */}

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}