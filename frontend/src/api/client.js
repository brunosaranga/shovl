// src/api/client.js
// Central axios instance — every API call in the app goes through this.
// Base URL reads from your .env so it points to localhost in dev
// and your real domain in production without changing any component code.

import axios from 'axios'

const client = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL, // e.g. http://localhost:8000/api
    headers: {
        'Content-Type': 'application/json',
    },
})

// Attach the JWT access token to every outgoing request automatically.
// Components never manually set Authorization headers.
// NOTE: the key here MUST match what AuthContext writes ('access_token').
client.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// If the backend returns 401, the token has expired or is missing.
// Clear storage and bounce the user to login — unless this was the
// login/register attempt itself (a 401 there just means bad credentials).
client.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            const url = error.config?.url || ''
            const isAuthEndpoint =
                url.includes('/accounts/login/') ||
                url.includes('/accounts/register/')

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
    add:    (data) => client.post('/domains/', data),     // { hostname }
    verify: (id)   => client.post(`/domains/${id}/verify/`),
    // NOTE: backend has no DELETE route for /domains/<id>/ yet — remove() will 404
    // until you add a DestroyAPIView. Left here so callers don't break on import.
    remove: (id)   => client.delete(`/domains/${id}/`),
}

export const scansAPI = {
    list:   ()     => client.get('/scans/'),
    create: (data) => client.post('/scans/create/', data), // { target_url, verbose, suggest_fix } — BLOCKING
    detail: (id)   => client.get(`/scans/${id}/`),
}

// The scan stream is an SSE endpoint. We can't use the axios client (and native
// EventSource can't send the Authorization header), so callers consume it with
// fetch() + a stream reader. This just builds the URL from the same base.
export function scanStreamUrl({ target_url, verbose = false, suggest_fix = false, generate_report = true }) {
    const base = import.meta.env.VITE_API_BASE_URL
    const params = new URLSearchParams({
        target_url,
        verbose: String(verbose),
        suggest_fix: String(suggest_fix),
        generate_report: String(generate_report),
    })
    return `${base}/scans/stream/?${params.toString()}`
}

export default client