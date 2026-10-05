import axios from 'axios';
import router from '@/router';
import { useAuthStore } from '@/stores/auth';

const client = axios.create({ baseURL: '/api' });

client.interceptors.request.use((cfg) => {
    const auth = useAuthStore();
    if (auth.token) cfg.headers.Authorization = `Bearer ${auth.token}`;
    return cfg;
});

client.interceptors.response.use(
    (r) => r,
    (err) => {
        if (err.response?.status === 401) {
            const auth = useAuthStore();
            auth.logout();
            if (router.currentRoute.value.name !== 'login') {
                router.push({ name: 'login' });
            }
        }
        return Promise.reject(err);
    }
);

export default client;
