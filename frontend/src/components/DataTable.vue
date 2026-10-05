<script setup>
import { onMounted, ref, watch } from 'vue';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import { bulkCreate, deleteEntity, exportEntity, listEntity } from '@/api/endpoints';

const props = defineProps({
    entity: { type: String, required: true },
    pkField: { type: String, required: true },
    columns: { type: Array, required: true }, // [{field, header, sortable?, body?}]
    filters: { type: Object, default: () => ({}) }, // extra GET params (reactive)
    searchable: { type: Boolean, default: true },
    allowSeed: { type: Boolean, default: true },
    allowExport: { type: Boolean, default: true }
});
const emit = defineEmits(['create', 'edit']);

const auth = useAuthStore();
const confirm = useConfirm();
const toast = useToast();

const rows = ref([]);
const totalRecords = ref(0);
const first = ref(0);
const rowsPerPage = ref(20);
const query = ref('');
const loading = ref(false);
const bulkCount = ref(5);
const exportFormat = ref('csv');
let debounceTimer = null;

async function load() {
    loading.value = true;
    try {
        const params = {
            page: Math.floor(first.value / rowsPerPage.value) + 1,
            pageSize: rowsPerPage.value,
            ...props.filters
        };
        if (query.value) params.search = query.value;
        const data = await listEntity(props.entity, params);
        rows.value = data.items;
        totalRecords.value = data.total;
    } finally {
        loading.value = false;
    }
}

watch(props.filters, () => {
    first.value = 0;
    load();
}, { deep: true });
watch([first, rowsPerPage], load);

function onSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        first.value = 0;
        load();
    }, 300);
}

function confirmDelete(row) {
    confirm.require({
        message: `Delete this ${props.entity.slice(0, -1)}? This cannot be undone.`,
        header: 'Confirm delete',
        icon: 'pi pi-exclamation-triangle',
        accept: () => doDelete(row)
    });
}

async function doDelete(row) {
    try {
        await deleteEntity(props.entity, row[props.pkField]);
        toast.add({ severity: 'success', summary: 'Deleted', detail: 'Record deleted' });
        if (rows.value.length === 1 && first.value > 0) first.value -= rowsPerPage.value;
        load();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Delete failed', detail: e.response?.data?.detail || e.message });
    }
}

function download(blob, name) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

async function doExport() {
    const stamp = new Date().toISOString().slice(0, 10);
    const blob = await exportEntity(
        props.entity,
        { pageSize: 1000, ...props.filters, search: query.value || undefined },
        exportFormat.value
    );
    download(blob, `${props.entity}_${stamp}.${exportFormat.value}`);
}

async function doBulk() {
    try {
        const res = await bulkCreate(props.entity, bulkCount.value);
        toast.add({ severity: 'success', summary: 'Bulk created', detail: `${res.inserted} record(s) created` });
        load();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Bulk failed', detail: e.response?.data?.detail || e.message });
    }
}

onMounted(load);
</script>

<template>
    <Card>
        <template #content>
            <div class="flex flex-wrap items-center gap-3 mb-4">
                <IconField v-if="props.searchable">
                    <InputIcon class="pi pi-search" />
                    <InputText v-model="query" placeholder="Search..." class="w-56" @input="onSearch" />
                </IconField>
                <div class="flex-1"></div>
                <div v-if="auth.isAdmin && props.allowSeed" class="flex items-center gap-2">
                    <InputNumber v-model="bulkCount" :min="1" :max="1000" showButtons buttonLayout="horizontal" decrementButtonClass="p-button-secondary" incrementButtonClass="p-button-secondary" incrementButtonIcon="pi pi-plus" decrementButtonIcon="pi pi-minus" style="width: 8rem" />
                    <Button label="Bulk add" icon="pi pi-database" text severity="secondary" @click="doBulk" />
                </div>
                <template v-if="props.allowExport">
                    <SelectButton v-model="exportFormat" :options="['csv', 'xlsx']" />
                    <Button label="Export" icon="pi pi-download" outlined @click="doExport" />
                </template>
                <Button v-if="auth.isAdmin" label="New" icon="pi pi-plus" @click="emit('create')" />
            </div>

            <DataTable
                :value="rows"
                :loading="loading"
                :totalRecords="totalRecords"
                :dataKey="props.pkField"
                lazy
                v-model:first="first"
                v-model:rows="rowsPerPage"
                :rowsPerPageOptions="[10, 20, 50, 100]"
                paginator
                :rowHover="true"
                responsiveLayout="scroll"
            >
                <Column v-for="col in props.columns" :key="col.field" :field="col.field" :header="col.header" :sortable="!!col.sortable">
                    <template #body="{ data }">
                        <span v-if="col.body">{{ col.body(data) }}</span>
                        <span v-else>{{ data[col.field] }}</span>
                    </template>
                </Column>
                <Column v-if="auth.isAdmin" header="Actions" style="min-width: 8rem">
                    <template #body="{ data }">
                        <Button icon="pi pi-pencil" text severity="secondary" v-tooltip.top="'Edit'" @click="emit('edit', data)" />
                        <Button icon="pi pi-trash" text severity="danger" v-tooltip.top="'Delete'" @click="confirmDelete(data)" />
                    </template>
                </Column>
            </DataTable>
        </template>
    </Card>
</template>
