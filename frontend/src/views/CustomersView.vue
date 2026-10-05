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
const model = ref({ full_name: '', email_address: '' });

const columns = [
    { field: 'customer_id', header: 'ID', sortable: true },
    { field: 'full_name', header: 'Name', sortable: true },
    { field: 'email_address', header: 'Email' }
];
const fields = [
    { name: 'full_name', label: 'Full Name', type: 'text', required: true },
    { name: 'email_address', label: 'Email', type: 'text', required: true }
];

function openCreate() {
    editingId.value = null;
    model.value = { full_name: '', email_address: '' };
    dialog.value = true;
}
function openEdit(row) {
    editingId.value = row.customer_id;
    model.value = { full_name: row.full_name, email_address: row.email_address };
    dialog.value = true;
}
async function save(payload) {
    saving.value = true;
    try {
        if (editingId.value) {
            await updateEntity('customers', editingId.value, payload);
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Customer updated' });
        } else {
            await createEntity('customers', payload);
            toast.add({ severity: 'success', summary: 'Created', detail: 'Customer created' });
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
        <h2 class="text-2xl font-semibold mb-4">Customers</h2>
        <DataTable entity="customers" pk-field="customer_id" :columns="columns" @create="openCreate" @edit="openEdit" />
        <CrudDialog v-model:visible="dialog" title="Customer" entity="customers" :fields="fields" :model="model" :saving="saving" @save="save" @close="dialog = false" />
    </div>
</template>
