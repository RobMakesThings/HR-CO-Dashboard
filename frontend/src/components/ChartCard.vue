<script setup>
defineProps({
    title: { type: String, required: true },
    loading: { type: Boolean, default: false },
    height: { type: String, default: '300px' }
});
</script>

<template>
    <Card>
        <template #title>
            <span class="font-semibold text-lg">{{ title }}</span>
        </template>
        <template #content>
            <div v-if="loading" class="flex items-center justify-center" :style="{ height }">
                <ProgressSpinner style="width: 40px; height: 40px" strokeWidth="4" />
            </div>
            <div v-else class="w-full" :style="{ height }">
                <slot />
            </div>
        </template>
    </Card>
</template>
