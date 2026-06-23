import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export default function ProtectedRoute() {
    const { accessToken } = useAuth()

    // Check localStorage directly as fallback for the
    // brief window between login() and React re-render
    const token = accessToken || localStorage.getItem('access_token')

    return token ? <Outlet /> : <Navigate to="/signin" replace />
}