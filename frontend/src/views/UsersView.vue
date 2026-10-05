<script setup>
import { ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import DataTable from '@/components/DataTable.vue';
import CrudDialog from '@/components/CrudDialog.vue';
import { createEntity, updateEntity } from '@/api/endpoints';

const toast = useToast();
const dialog = ref(false);
const saving = ref(false);
const editingId = ref(null);
const model = ref({ username: '', password: '', role: 'viewer' });

const roleOptions = [
    { label: 'Admin', value: 'admin' },
    { label: 'Viewer', value: 'viewer' }
];

const columns = [
    { field: 'app_user_id', header: 'ID' },
    { field: 'username', header: 'Username', sortable: true },
    { field: 'role', header: 'Role', body: (r) => r.role },
    { field: 'created_at', header: 'Created' }
];
const fields = [
    { name: 'username', label: 'Username', type: 'text', required: true },
    { name: 'password', label: 'Password', type: 'password', required: true },
    { name: 'role', label: 'Role', type: 'select', options: roleOptions, required: true }
];

function openCreate() {
    editingId.value = null;
    model.value = { username: '', password: '', role: 'viewer' };
    dialog.value = true;
}
function openEdit(row) {
    editingId.value = row.app_user_id;
    model.value = { username: row.username, password: '', role: row.role };
    dialog.value = true;
}
async function save(payload) {
    saving.value = true;
    try {
        if (editingId.value) {
            const body = {};
            if (payload.password) body.password = payload.password;
            if (payload.role) body.role = payload.role;
            await updateEntity('users', editingId.value, body);
            toast.add({ severity: 'success', summary: 'Updated', detail: 'User updated' });
        } else {
            await createEntity('users', payload);
            toast.add({ severity: 'success', summary: 'Created', detail: 'User created' });
        }
        dialog.value = false;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Error', detail: e.response?.data?.detail || e.message });
    } finally {
        saving.value = false;
    }
}
</script>

<template>
    <div class="p-6">
        <h2 class="text-2xl font-semibold mb-4">Users (Admin)</h2>
        <DataTable entity="users" pk-field="app_user_id" :columns="columns" :allow-seed="false" :allow-export="false" :searchable="false" @create="openCreate" @edit="openEdit" />
        <CrudDialog v-model:visible="dialog" title="User" :fields="fields" :model="model" :saving="saving" @save="save" @close="dialog = false" />
    </div>
</template>
