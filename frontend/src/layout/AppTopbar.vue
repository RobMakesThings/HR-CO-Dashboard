<script setup>
import { useRouter } from 'vue-router';
import { useLayout } from '@/layout/composables/layout';
import AppConfigurator from './AppConfigurator.vue';
import { useAuthStore } from '@/stores/auth';

const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const auth = useAuthStore();
const router = useRouter();

function logout() {
    auth.logout();
    router.push({ name: 'login' });
}
</script>

<template>
    <div class="layout-topbar">
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>
            <router-link to="/" class="layout-topbar-logo">
                <i class="pi pi-chart-line" style="color: var(--primary-color); font-size: 1.6rem"></i>
                <span>HR + CO</span>
            </router-link>
        </div>

        <div class="layout-topbar-actions">
            <div class="layout-config-menu">
                <button type="button" class="layout-topbar-action" @click="toggleDarkMode">
                    <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
                </button>
                <div class="relative">
                    <button
                        v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'p-anchored-overlay-enter-active', leaveToClass: 'hidden', leaveActiveClass: 'p-anchored-overlay-leave-active', hideOnOutsideClick: true }"
                        type="button"
                        class="layout-topbar-action layout-topbar-action-highlight"
                    >
                        <i class="pi pi-palette"></i>
                    </button>
                    <AppConfigurator />
                </div>
            </div>

            <div class="layout-topbar-menu hidden lg:block">
                <div class="layout-topbar-menu-content">
                    <div class="flex items-center gap-3 px-3">
                        <span class="font-medium">{{ auth.username }}</span>
                        <span
                            class="px-2 py-0.5 text-xs font-semibold uppercase rounded-full"
                            :class="auth.isAdmin ? 'bg-primary text-white' : 'bg-surface-200 text-surface-700'"
                        >
                            {{ auth.role }}
                        </span>
                        <button type="button" class="layout-topbar-action" @click="logout">
                            <i class="pi pi-sign-out"></i>
                            <span>Logout</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
