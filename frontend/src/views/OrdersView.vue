<script setup>
import { onMounted, ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import DataTable from '@/components/DataTable.vue';
import DateRangePicker from '@/components/DateRangePicker.vue';
import { createEntity, getEntity, lookup, updateEntity } from '@/api/endpoints';

const toast = useToast();
const customers = ref([]);
const stores = ref([]);
const statuses = ref([]);
const products = ref([]);
const range = ref(null);

const filters = ref({ status: null, customer_id: null, store_id: null, date_from: null, date_to: null });

const dialogVisible = ref(false);
const saving = ref(false);
const editingId = ref(null);
const draft = ref({
    customer_id: null,
    store_id: null,
    order_status: null,
    order_tms: new Date(),
    items: [{ product_id: null, quantity: 1, unit_price: null }]
});

const currency = (v) => (v == null ? '' : `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
const dateFmt = (v) => (v ? String(v).slice(0, 10) : '');

const columns = [
    { field: 'order_id', header: 'Order', sortable: true },
    { field: 'order_tms', header: 'Date', body: (r) => dateFmt(r.order_tms) },
    { field: 'customer_name', header: 'Customer' },
    { field: 'store_name', header: 'Store' },
    { field: 'order_status', header: 'Status' },
    { field: 'total', header: 'Total', body: (r) => currency(r.total) },
    { field: 'item_count', header: 'Items' }
];

onMounted(async () => {
    const [c, s, st, p] = await Promise.all([
        lookup('customers'), lookup('stores'), lookup('order-statuses'), lookup('products')
    ]);
    customers.value = c.map((x) => ({ label: x.full_name, value: x.customer_id }));
    stores.value = s.map((x) => ({ label: x.store_name, value: x.store_id }));
    statuses.value = st.map((x) => x.order_status);
    products.value = p.map((x) => ({ label: `${x.product_name} (${currency(x.unit_price)})`, value: x.product_id, unit_price: x.unit_price }));
});

function onRange(v) {
    filters.value.date_from = v.from;
    filters.value.date_to = v.to;
}
function newLine() {
    draft.value.items.push({ product_id: null, quantity: 1, unit_price: null });
}
function removeLine(i) {
    draft.value.items.splice(i, 1);
}
function onPickProduct(it, val) {
    const opt = products.value.find((p) => p.value === val);
    it.unit_price = opt ? opt.unit_price : it.unit_price;
}
function openCreate() {
    editingId.value = null;
    draft.value = {
        customer_id: null, store_id: null, order_status: null, order_tms: new Date(),
        items: [{ product_id: null, quantity: 1, unit_price: null }]
    };
    dialogVisible.value = true;
}
async function openEdit(row) {
    editingId.value = row.order_id;
    const data = await getEntity('orders', row.order_id);
    draft.value = {
        customer_id: data.customer_id,
        store_id: data.store_id,
        order_status: data.order_status,
        order_tms: data.order_tms ? new Date(data.order_tms) : new Date(),
        items: data.items.length
            ? data.items.map((it) => ({ product_id: it.product_id, quantity: it.quantity, unit_price: it.unit_price }))
            : [{ product_id: null, quantity: 1, unit_price: null }]
    };
    dialogVisible.value = true;
}
function buildPayload() {
    return {
        customer_id: draft.value.customer_id,
        store_id: draft.value.store_id,
        order_status: draft.value.order_status,
        order_tms: draft.value.order_tms ? draft.value.order_tms.toISOString() : null,
        items: draft.value.items
            .filter((it) => it.product_id)
            .map((it) => ({ product_id: it.product_id, quantity: it.quantity, unit_price: it.unit_price }))
    };
}
async function save() {
    saving.value = true;
    try {
        const payload = buildPayload();
        if (editingId.value) {
            await updateEntity('orders', editingId.value, payload);
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Order updated' });
        } else {
            await createEntity('orders', payload);
            toast.add({ severity: 'success', summary: 'Created', detail: 'Order created' });
        }
        dialogVisible.value = false;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Error', detail: e.response?.data?.detail || e.message });
    } finally {
        saving.value = false;
    }
}
</script>

<template>
    <div class="p-6">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 class="text-2xl font-semibold">Orders</h2>
            <div class="flex flex-wrap items-center gap-3">
                <Select v-model="filters.status" :options="statuses" placeholder="Status" showClear class="w-36" />
                <Select v-model="filters.customer_id" :options="customers" optionLabel="label" optionValue="value" placeholder="Customer" showClear class="w-56" />
                <Select v-model="filters.store_id" :options="stores" optionLabel="label" optionValue="value" placeholder="Store" showClear class="w-48" />
                <DateRangePicker v-model="range" @update:modelValue="onRange" />
            </div>
        </div>

        <DataTable
            entity="orders"
            pk-field="order_id"
            :columns="columns"
            :filters="{ status: filters.status, customer_id: filters.customer_id, store_id: filters.store_id, date_from: filters.date_from, date_to: filters.date_to }"
            @create="openCreate"
            @edit="openEdit"
        />

        <Dialog v-model:visible="dialogVisible" :header="editingId ? 'Edit Order' : 'New Order'" :modal="true" :closable="false" :style="{ width: '680px' }" @hide="dialogVisible = false">
            <div class="flex flex-col gap-4">
                <div class="grid grid-cols-2 gap-4">
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium">Customer *</label>
                        <Select v-model="draft.customer_id" :options="customers" optionLabel="label" optionValue="value" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium">Store *</label>
                        <Select v-model="draft.store_id" :options="stores" optionLabel="label" optionValue="value" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium">Status *</label>
                        <Select v-model="draft.order_status" :options="statuses" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium">Order Date *</label>
                        <Calendar v-model="draft.order_tms" showTime dateFormat="yy-mm-dd" />
                    </div>
                </div>

                <div class="flex items-center justify-between">
                    <span class="text-sm font-medium">Line Items</span>
                    <Button label="Add line" icon="pi pi-plus" text severity="secondary" @click="newLine" />
                </div>

                <div v-for="(it, i) in draft.items" :key="i" class="grid grid-cols-[1fr_7rem_7rem_auto] gap-2 items-center">
                    <Select
                        v-model="it.product_id"
                        :options="products"
                        optionLabel="label"
                        optionValue="value"
                        :filter="true"
                        @update:modelValue="onPickProduct(it, $event)"
                    />
                    <InputNumber v-model="it.quantity" :min="1" integerOnly />
                    <InputNumber v-model="it.unit_price" mode="decimal" :minFractionDigits="2" :maxFractionDigits="2" />
                    <Button icon="pi pi-trash" text severity="danger" @click="removeLine(i)" />
                </div>
            </div>
            <template #footer>
                <Button label="Cancel" icon="pi pi-times" text @click="dialogVisible = false" />
                <Button label="Save" icon="pi pi-check" :loading="saving" @click="save" />
            </template>
        </Dialog>
    </div>
</template>
