import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/login',
            name: 'login',
            component: () => import('@/views/LoginView.vue'),
            meta: { public: true }
        },
        {
            path: '/',
            component: AppLayout,
            children: [
                {
                    path: '',
                    name: 'dashboard',
                    component: () => import('@/views/DashboardView.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: 'employees',
                    name: 'employees',
                    component: () => import('@/views/EmployeesView.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: 'orders',
                    name: 'orders',
                    component: () => import('@/views/OrdersView.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: 'customers',
                    name: 'customers',
                    component: () => import('@/views/CustomersView.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: 'products',
                    name: 'products',
                    component: () => import('@/views/ProductsView.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: 'users',
                    name: 'users',
                    component: () => import('@/views/UsersView.vue'),
                    meta: { requiresAuth: true, adminOnly: true }
                }
            ]
        },
        {
            path: '/:pathMatch(.*)*',
            redirect: '/'
        }
    ]
});

router.beforeEach((to) => {
    const auth = useAuthStore();
    if (!to.meta.public && !auth.token) return { name: 'login' };
    if (to.meta.adminOnly && auth.role !== 'admin') return { name: 'dashboard' };
    if (to.name === 'login' && auth.token) return { name: 'dashboard' };
});

export default router;
