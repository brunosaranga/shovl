import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute() {
    const { accessToken } = useAuth()
    return accessToken ? <Outlet /> : <Navigate to="/signin" replace />
}