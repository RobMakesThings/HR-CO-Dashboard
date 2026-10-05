<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const router = useRouter();
const toast = useToast();

const username = ref('');
const password = ref('');
const loading = ref(false);

async function submit() {
    loading.value = true;
    try {
        await auth.login(username.value, password.value);
        router.push({ name: 'dashboard' });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Login failed', detail: e.response?.data?.detail || 'Invalid credentials' });
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="min-h-screen flex items-center justify-center p-4">
        <Card class="w-full max-w-md">
            <template #title>
                <div class="flex items-center gap-3">
                    <i class="pi pi-chart-line text-2xl" style="color: var(--primary-color)"></i>
                    <span class="text-xl font-semibold">HR + CO Dashboard</span>
                </div>
            </template>
            <template #content>
                <form class="flex flex-col gap-4" @submit.prevent="submit">
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium" for="username">Username</label>
                        <InputText id="username" v-model="username" autocomplete="username" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium" for="password">Password</label>
                        <Password id="password" v-model="password" :feedback="false" toggleMask autocomplete="current-password" />
                    </div>
                    <Button label="Sign in" icon="pi pi-sign-in" type="submit" :loading="loading" class="mt-2" />
                </form>
            </template>
        </Card>
    </div>
</template>
