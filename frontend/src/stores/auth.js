import { defineStore } from 'pinia';
import client from '@/api/client';

export const useAuthStore = defineStore('auth', {
    state: () => ({
        token: localStorage.getItem('token') || null,
        username: localStorage.getItem('username') || null,
        role: localStorage.getItem('role') || null
    }),
    getters: {
        isAdmin: (s) => s.role === 'admin'
    },
    actions: {
        async login(username, password) {
            const { data } = await client.post('/auth/login', { username, password });
            this.token = data.access_token;
            this.username = data.username;
            this.role = data.role;
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', data.username);
            localStorage.setItem('role', data.role);
        },
        logout() {
            this.token = null;
            this.username = null;
            this.role = null;
            localStorage.removeItem('token');
            localStorage.removeItem('username');
            localStorage.removeItem('role');
        }
    }
});
