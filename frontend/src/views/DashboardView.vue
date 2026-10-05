<script setup>
import { onMounted, ref } from 'vue';
import ChartCard from '@/components/ChartCard.vue';
import DateRangePicker from '@/components/DateRangePicker.vue';
import client from '@/api/client';

const range = ref(defaultRange());
const loading = ref(false);

const revenueData = ref(null);
const statusData = ref(null);
const topProducts = ref([]);
const storeRevenue = ref(null);
const topCustomers = ref([]);
const headcount = ref(null);
const salaryJob = ref(null);
const salaryDist = ref(null);
const hires = ref(null);

function defaultRange() {
    const to = new Date();
    const from = new Date();
    from.setFullYear(to.getFullYear() - 1);
    return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) };
}
function onRange(v) {
    range.value = v;
    load();
}
async function get(path, params) {
    const r = await client.get(`/analytics/${path}`, { params });
    return r.data;
}
function buildLine(points, label) {
    return {
        labels: points.map((p) => String(p.period || p.year || '').slice(0, 7)),
        datasets: [{ label, data: points.map((p) => p.revenue ?? p.cnt), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,.2)', fill: true, tension: 0.3 }]
    };
}
function buildBar(series, label, keyX, keyY) {
    return {
        labels: series.map((s) => s[keyX]),
        datasets: [{ label, data: series.map((s) => s[keyY]), backgroundColor: '#3b82f6' }]
    };
}
function buildPie(series) {
    return {
        labels: series.map((s) => s.status),
        datasets: [{ data: series.map((s) => s.count), backgroundColor: ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4'] }]
    };
}
async function load() {
    loading.value = true;
    try {
        const params = { from: range.value.from, to: range.value.to };
        const [rev, status, tp, srev, tc, hc, sal, hir] = await Promise.all([
            get('revenue-over-time', { ...params, granularity: 'month' }),
            get('orders-by-status', params),
            get('top-products', { ...params, limit: 8 }),
            get('revenue-by-store', params),
            get('top-customers', { ...params, limit: 10 }),
            get('headcount-by-dept'),
            get('salary-stats'),
            get('hires-over-time')
        ]);
        revenueData.value = buildLine(rev.points, 'Revenue');
        statusData.value = buildPie(status.series);
        topProducts.value = tp.series;
        storeRevenue.value = buildBar(srev.series, 'Revenue', 'store_name', 'revenue');
        topCustomers.value = tc.series;
        headcount.value = buildBar(hc.series, 'Employees', 'department_name', 'cnt');
        salaryJob.value = buildBar(sal.by_job, 'Avg salary', 'job_title', 'avg_sal');
        salaryDist.value = buildBar(sal.distribution, 'Employees', 'bucket', 'cnt');
        hires.value = buildLine(hir.points, 'New hires');
    } finally {
        loading.value = false;
    }
}
const currency = (v) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const axisOpts = { responsive: true, maintainAspectRatio: false };

onMounted(load);
</script>

<template>
    <div class="p-6">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
            <h2 class="text-2xl font-semibold">Dashboard</h2>
            <DateRangePicker :model-value="range" @update:modelValue="onRange" />
        </div>

        <div v-if="loading" class="flex justify-center py-20">
            <ProgressSpinner style="width: 60px; height: 60px" strokeWidth="5" />
        </div>

        <template v-else>
            <h3 class="text-lg font-semibold mb-3">Orders &amp; Customers</h3>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
                <ChartCard title="Revenue over time (monthly)" :loading="false">
                    <Chart v-if="revenueData" type="line" :data="revenueData" :options="axisOpts" style="height: 300px" />
                </ChartCard>
                <ChartCard title="Orders by status" :loading="false">
                    <Chart v-if="statusData" type="pie" :data="statusData" :options="{ responsive: true, maintainAspectRatio: false }" style="height: 300px" />
                </ChartCard>
                <ChartCard title="Top products by revenue" :loading="false">
                    <Chart v-if="topProducts.length" type="bar" :data="{ labels: topProducts.map((p) => p.product_name), datasets: [{ label: 'Revenue', data: topProducts.map((p) => p.revenue), backgroundColor: '#3b82f6' }] }" :options="axisOpts" style="height: 300px" />
                </ChartCard>
                <ChartCard title="Revenue by store" :loading="false">
                    <Chart v-if="storeRevenue" type="bar" :data="storeRevenue" :options="axisOpts" style="height: 300px" />
                </ChartCard>
                <ChartCard title="Top customers by spend" :loading="false">
                    <div class="w-full">
                        <DataTable :value="topCustomers" :rows="10" responsiveLayout="scroll" class="w-full">
                            <Column field="full_name" header="Customer" />
                            <Column field="spend" header="Spend">
                                <template #body="{ data }">{{ currency(data.spend) }}</template>
                            </Column>
                        </DataTable>
                    </div>
                </ChartCard>
            </div>

            <h3 class="text-lg font-semibold mb-3">Employees</h3>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ChartCard title="Headcount by department" :loading="false">
                    <Chart v-if="headcount" type="bar" :data="headcount" :options="axisOpts" style="height: 300px" />
                </ChartCard>
                <ChartCard title="Average salary by job" :loading="false">
                    <Chart v-if="salaryJob" type="bar" :data="salaryJob" :options="axisOpts" style="height: 300px" />
                </ChartCard>
                <ChartCard title="Salary distribution" :loading="false">
                    <Chart v-if="salaryDist" type="bar" :data="salaryDist" :options="axisOpts" style="height: 300px" />
                </ChartCard>
                <ChartCard title="Hires over time (by year)" :loading="false">
                    <Chart v-if="hires" type="line" :data="hires" :options="axisOpts" style="height: 300px" />
                </ChartCard>
            </div>
        </template>
    </div>
</template>
