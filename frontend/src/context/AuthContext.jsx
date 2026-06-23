import { createContext, useState } from 'react'

export const AuthContext = createContext(null)  // <-- add export here

export function AuthProvider({ children }) {
    const [accessToken, setAccessToken] = useState(
        () => localStorage.getItem('access_token') || null
    )
    const [user, setUser] = useState(
        () => {
            const stored = localStorage.getItem('user')
            return stored ? JSON.parse(stored) : null
        }
    )

    const login = (tokens, userData) => {
        localStorage.setItem('access_token', tokens.access)
        localStorage.setItem('user', JSON.stringify(userData))
        setAccessToken(tokens.access)
        setUser(userData)
    }

    const logout = () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        setAccessToken(null)
        setUser(null)
    }

    return (
        <AuthContext.Provider value={{ accessToken, user, login, logout }}>
            {children}
        </AuthContext.Provider>
    )
}