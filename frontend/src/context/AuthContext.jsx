import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [accessToken, setAccessToken] = useState(null)
    const [user, setUser] = useState(null)

    const login = (tokens, userData) => {
        setAccessToken(tokens.access)
        setUser(userData)
    }

    const logout = () => {
        setAccessToken(null)
        setUser(null)
    }

    return (
        <AuthContext.Provider value={{ accessToken, user, login, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => useContext(AuthContext)