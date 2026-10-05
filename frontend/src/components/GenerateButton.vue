<script setup>
import { ref } from 'vue';
import { generateEntity } from '@/api/endpoints';

const props = defineProps({
    entity: { type: String, required: true }
});
const emit = defineEmits(['filled']);

const loading = ref(false);

async function fill() {
    loading.value = true;
    try {
        const data = await generateEntity(props.entity);
        emit('filled', data);
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <Button type="button" label="Generate" icon="pi pi-dice" text severity="secondary" :loading="loading" @click="fill" />
</template>
