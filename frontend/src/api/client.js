import axios from 'axios'

const client = axios.create({
    baseURL: 'http://localhost:8000/api',
    headers: { 'Content-Type': 'application/json'}
})

// Attach token to every request
client.interceptors.request.use(config => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

export const authAPI = {
    login:    (data) => client.post('/accounts/login/', data),
    register: (data) => client.post('/accounts/register/', data),
    me:       ()     => client.get('/accounts/me/'),
}

export const domainsAPI = {
    list:   ()       => client.get('/domains/'),
    add:    (data)   => client.post('/domains/', data),
    verify: (id)     => client.post(`/domains/${id}/verify/`),
    remove: (id)     => client.delete(`/domains/${id}/`),
}

export default client