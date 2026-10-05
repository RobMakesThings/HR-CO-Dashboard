<script setup>
import { onMounted, ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import DataTable from '@/components/DataTable.vue';
import CrudDialog from '@/components/CrudDialog.vue';
import { createEntity, lookup, updateEntity } from '@/api/endpoints';

const toast = useToast();
const dialog = ref(false);
const saving = ref(false);
const editingId = ref(null);
const model = ref({});
const filters = ref({ department_id: null, job_id: null });

const departments = ref([]);
const jobs = ref([]);
const managers = ref([]);

const currency = (v) => (v == null ? '' : `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
const dateFmt = (v) => (v ? String(v).slice(0, 10) : '');

const columns = [
    { field: 'employee_id', header: 'ID', sortable: true },
    { field: 'first_name', header: 'First' },
    { field: 'last_name', header: 'Last' },
    { field: 'email', header: 'Email' },
    { field: 'job_title', header: 'Job' },
    { field: 'department_name', header: 'Department' },
    { field: 'salary', header: 'Salary', body: (r) => currency(r.salary) },
    { field: 'hire_date', header: 'Hired', body: (r) => dateFmt(r.hire_date) }
];

const fields = [
    { name: 'first_name', label: 'First Name', type: 'text' },
    { name: 'last_name', label: 'Last Name', type: 'text', required: true },
    { name: 'email', label: 'Email', type: 'text', required: true },
    { name: 'phone_number', label: 'Phone', type: 'text' },
    { name: 'hire_date', label: 'Hire Date', type: 'date', required: true },
    { name: 'job_id', label: 'Job', type: 'select', options: jobs, required: true },
    { name: 'salary', label: 'Salary', type: 'number', fraction: 2 },
    { name: 'commission_pct', label: 'Commission %', type: 'number', fraction: 2 },
    { name: 'manager_id', label: 'Manager', type: 'select', options: managers },
    { name: 'department_id', label: 'Department', type: 'select', options: departments }
];

onMounted(async () => {
    const [d, j, m] = await Promise.all([lookup('departments'), lookup('jobs'), lookup('managers')]);
    departments.value = d.map((x) => ({ label: x.department_name, value: x.department_id }));
    jobs.value = j.map((x) => ({ label: x.job_title, value: x.job_id }));
    managers.value = m.map((x) => ({ label: x.name, value: x.employee_id }));
});

function openCreate() {
    editingId.value = null;
    model.value = {};
    dialog.value = true;
}
function openEdit(row) {
    editingId.value = row.employee_id;
    model.value = {
        first_name: row.first_name, last_name: row.last_name, email: row.email,
        phone_number: row.phone_number, hire_date: row.hire_date ? new Date(row.hire_date) : null,
        job_id: row.job_id, salary: row.salary, commission_pct: row.commission_pct,
        manager_id: row.manager_id, department_id: row.department_id
    };
    dialog.value = true;
}
async function save(payload) {
    saving.value = true;
    try {
        if (editingId.value) {
            await updateEntity('employees', editingId.value, payload);
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Employee updated' });
        } else {
            await createEntity('employees', payload);
            toast.add({ severity: 'success', summary: 'Created', detail: 'Employee created' });
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
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 class="text-2xl font-semibold">Employees</h2>
            <div class="flex flex-wrap items-center gap-3">
                <Select v-model="filters.department_id" :options="departments" optionLabel="label" optionValue="value" placeholder="Department" showClear class="w-56" />
                <Select v-model="filters.job_id" :options="jobs" optionLabel="label" optionValue="value" placeholder="Job" showClear class="w-56" />
            </div>
        </div>
        <DataTable entity="employees" pk-field="employee_id" :columns="columns" :filters="filters" @create="openCreate" @edit="openEdit" />
        <CrudDialog v-model:visible="dialog" title="Employee" entity="employees" :fields="fields" :model="model" :saving="saving" @save="save" @close="dialog = false" />
    </div>
</template>
