<template>
  <div v-if="items.length" class="discussion-linked-targets" :class="{ 'discussion-linked-targets--compact': compact }">
    <button
      v-for="item in items"
      :key="targetKey(item)"
      type="button"
      class="discussion-linked-target"
      :class="{
        'discussion-linked-target--clickable': clickable && item.available,
        'discussion-linked-target--unavailable': item.available === false
      }"
      :disabled="clickable ? item.available === false : false"
      @click="onOpen(item)"
    >
      <span class="discussion-linked-target__eyebrow">
        <span class="discussion-linked-target__type">{{ item.target_label }}</span>
        <span v-if="item.available === false" class="discussion-linked-target__status">不可用</span>
      </span>
      <strong class="discussion-linked-target__title">{{ item.title }}</strong>
      <span v-if="item.secondary_text" class="discussion-linked-target__secondary">{{ item.secondary_text }}</span>
      <span
        v-if="removable"
        class="discussion-linked-target__remove"
        role="button"
        tabindex="0"
        @click.stop="$emit('remove', item)"
        @keydown.enter.stop.prevent="$emit('remove', item)"
      >
        移除
      </span>
    </button>
  </div>
</template>

<script setup>
import { discussionLinkedTargetKey as targetKey } from '@/utils/discussionLinkTargets'

defineProps({
  items: {
    type: Array,
    default: () => []
  },
  removable: {
    type: Boolean,
    default: false
  },
  clickable: {
    type: Boolean,
    default: false
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['open', 'remove'])

const onOpen = item => {
  emit('open', item)
}
</script>

<style scoped>
.discussion-linked-targets {
  display: grid;
  gap: 10px;
  margin-top: 10px;
}

.discussion-linked-targets--compact {
  gap: 8px;
  margin-top: 8px;
}

.discussion-linked-target {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.98)),
    linear-gradient(120deg, rgba(14, 165, 233, 0.06), rgba(59, 130, 246, 0.02));
  text-align: left;
}

.discussion-linked-target--clickable {
  cursor: pointer;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease,
    border-color 0.16s ease;
}

.discussion-linked-target--clickable:hover {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.3);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.discussion-linked-target--unavailable {
  opacity: 0.78;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(241, 245, 249, 0.98));
}

.discussion-linked-target__eyebrow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.discussion-linked-target__type {
  color: #0369a1;
  font-weight: 700;
}

.discussion-linked-target__status {
  color: #b45309;
  font-weight: 600;
}

.discussion-linked-target__title {
  color: #0f172a;
  font-size: 14px;
  line-height: 1.45;
}

.discussion-linked-target__secondary {
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.discussion-linked-target__remove {
  color: #dc2626;
  font-size: 12px;
  font-weight: 600;
  justify-self: start;
}
</style>
