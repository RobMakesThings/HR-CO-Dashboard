<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
    modelValue: { type: Object, default: () => ({ from: null, to: null }) }
});
const emit = defineEmits(['update:modelValue']);

const dates = ref(props.modelValue?.from ? [new Date(props.modelValue.from), new Date(props.modelValue.to)] : null);

watch(
    () => props.modelValue,
    (v) => {
        const next = v?.from ? [new Date(v.from), new Date(v.to)] : null;
        if (!next) dates.value = null;
    }
);

function onChange(d) {
    if (d && d.length === 2) {
        emit('update:modelValue', { from: d[0].toISOString().slice(0, 10), to: d[1].toISOString().slice(0, 10) });
    } else {
        emit('update:modelValue', { from: null, to: null });
    }
}
</script>

<template>
    <DatePicker v-model="dates" selectionMode="range" :manualInput="false" showIcon dateFormat="yy-mm-dd" @update:modelValue="onChange" />
</template>
