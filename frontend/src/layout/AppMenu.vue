<script setup>
import { computed } from 'vue';
import AppMenuItem from './AppMenuItem.vue';
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();

const model = computed(() => {
    const menu = [
        {
            label: 'Overview',
            items: [{ label: 'Dashboard', icon: 'pi pi-fw pi-home', to: '/' }]
        },
        {
            label: 'Sales',
            items: [
                { label: 'Orders', icon: 'pi pi-fw pi-th-large', to: '/orders' },
                { label: 'Customers', icon: 'pi pi-fw pi-users', to: '/customers' },
                { label: 'Products', icon: 'pi pi-fw pi-box', to: '/products' }
            ]
        },
        {
            label: 'Human Resources',
            items: [{ label: 'Employees', icon: 'pi pi-fw pi-id-card', to: '/employees' }]
        }
    ];
    if (auth.isAdmin) {
        menu.push({
            label: 'Administration',
            items: [{ label: 'Users', icon: 'pi pi-fw pi-user-edit', to: '/users' }]
        });
    }
    return menu;
});
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item.label">
            <app-menu-item v-if="!item.separator" :item="item" :index="i"></app-menu-item>
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>

<style lang="scss" scoped></style>
