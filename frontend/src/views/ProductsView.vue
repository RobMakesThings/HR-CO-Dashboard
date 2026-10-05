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
const model = ref({ product_name: '', unit_price: null });

const currency = (v) => (v == null ? '' : `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);

const columns = [
    { field: 'product_id', header: 'ID', sortable: true },
    { field: 'product_name', header: 'Name', sortable: true },
    { field: 'unit_price', header: 'Unit Price', body: (r) => currency(r.unit_price) }
];
const fields = [
    { name: 'product_name', label: 'Product Name', type: 'text', required: true },
    { name: 'unit_price', label: 'Unit Price', type: 'number', min: 0, fraction: 2 }
];

function openCreate() {
    editingId.value = null;
    model.value = { product_name: '', unit_price: null };
    dialog.value = true;
}
function openEdit(row) {
    editingId.value = row.product_id;
    model.value = { product_name: row.product_name, unit_price: row.unit_price };
    dialog.value = true;
}
async function save(payload) {
    saving.value = true;
    try {
        if (editingId.value) {
            await updateEntity('products', editingId.value, payload);
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Product updated' });
        } else {
            await createEntity('products', payload);
            toast.add({ severity: 'success', summary: 'Created', detail: 'Product created' });
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
        <h2 class="text-2xl font-semibold mb-4">Products</h2>
        <DataTable entity="products" pk-field="product_id" :columns="columns" @create="openCreate" @edit="openEdit" />
        <CrudDialog v-model:visible="dialog" title="Product" entity="products" :fields="fields" :model="model" :saving="saving" @save="save" @close="dialog = false" />
    </div>
</template>
