// src/api/client.js
// Central axios instance — every API call in the app goes through this.
// Base URL reads from your .env so it points to localhost in dev
// and your real domain in production without changing any component code.

import axios from 'axios'

const client = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL, // e.g. http://localhost:8000
    headers: {
        'Content-Type': 'application/json',
    },
})

// Attach the JWT access token to every outgoing request automatically.
// Components never manually set Authorization headers.
client.interceptors.request.use((config) => {
    const token = localStorage.getItem('accessToken')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// If the backend returns 401, the token has expired.
// Clear storage and bounce the user to login.
client.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            const isAuthEndpoint = error.config.url.includes('/accounts/login/') ||
                                   error.config.url.includes('/accounts/register/')

            // Only bounce to signin if this was NOT a login/register attempt
            if (!isAuthEndpoint) {
                localStorage.removeItem('access_token')
                localStorage.removeItem('user')
                window.location.href = '/signin'
            }
        }
        return Promise.reject(error)
    }
)

export const authAPI = {
    login:    (data) => client.post('/accounts/login/', data),
    register: (data) => client.post('/accounts/register/', data),
    me:       (token) => client.get('/accounts/me/', {
        headers: { Authorization: `Bearer ${token}` }
    }),
}

export const domainsAPI = {
    list:   ()     => client.get('/domains/'),
    add:    (data) => client.post('/domains/', data),
    verify: (id)   => client.post(`/domains/${id}/verify/`),
    remove: (id)   => client.delete(`/domains/${id}/`),
}

export default client