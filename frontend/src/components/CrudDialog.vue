<script setup>
import { ref, watch } from 'vue';
import GenerateButton from './GenerateButton.vue';

const props = defineProps({
    visible: { type: Boolean, default: false },
    title: { type: String, required: true },
    fields: { type: Array, required: true }, // [{name,label,type,options?,required?,placeholder?,min?,fraction?}]
    model: { type: Object, required: true },
    saving: { type: Boolean, default: false },
    entity: { type: String, default: '' } // when set, shows a Generate button
});
const emit = defineEmits(['save', 'close']);

const draft = ref({ ...props.model });

watch(
    () => props.visible,
    () => {
        if (props.visible) draft.value = { ...props.model };
    }
);

function toSave() {
    const out = { ...draft.value };
    for (const f of props.fields) {
        if (f.type === 'date' && out[f.name] instanceof Date) {
            out[f.name] = out[f.name].toISOString().slice(0, 10);
        }
    }
    return out;
}

function onGenerated(data) {
    const merged = { ...draft.value, ...data };
    for (const f of props.fields) {
        if (f.type === 'date' && merged[f.name] && typeof merged[f.name] === 'string') {
            merged[f.name] = new Date(merged[f.name]);
        }
    }
    draft.value = merged;
}

function save() {
    emit('save', toSave());
}
</script>

<template>
    <Dialog :visible="props.visible" :header="props.title" :modal="true" :closable="false" :style="{ width: '540px' }" @hide="emit('close')">
        <div class="flex flex-col gap-4">
            <div v-if="props.entity" class="flex justify-end">
                <GenerateButton :entity="props.entity" @filled="onGenerated" />
            </div>
            <div v-for="f in props.fields" :key="f.name" class="flex flex-col gap-1">
                <label class="text-sm font-medium">
                    {{ f.label }}<span v-if="f.required" class="text-red-500"> *</span>
                </label>
                <Select
                    v-if="f.type === 'select'"
                    v-model="draft[f.name]"
                    :options="f.options"
                    optionLabel="label"
                    optionValue="value"
                    :placeholder="f.placeholder || 'Select...'"
                    :showClear="!f.required"
                />
                <InputNumber
                    v-else-if="f.type === 'number'"
                    v-model="draft[f.name]"
                    mode="decimal"
                    :min="f.min"
                    :minFractionDigits="f.fraction ?? 0"
                    :maxFractionDigits="f.fraction ?? 2"
                />
                <Calendar
                    v-else-if="f.type === 'date'"
                    v-model="draft[f.name]"
                    dateFormat="yy-mm-dd"
                    showIcon
                />
                <Password
                    v-else-if="f.type === 'password'"
                    v-model="draft[f.name]"
                    :feedback="false"
                    toggleMask
                />
                <InputText v-else v-model="draft[f.name]" />
            </div>
        </div>
        <template #footer>
            <Button label="Cancel" icon="pi pi-times" text @click="emit('close')" />
            <Button label="Save" icon="pi pi-check" :loading="props.saving" @click="save" />
        </template>
    </Dialog>
</template>
