<template>
  <div class="schedule-picker">
    <el-alert
      v-if="legacyValue"
      type="warning"
      :closable="false"
      class="schedule-picker__legacy"
    >
      当前课程使用的是旧版手填时间：{{ legacyValue }}。保存时请重新勾选下面的周几与节次。
    </el-alert>

    <div class="schedule-picker__toolbar">
      <div>
        <div class="schedule-picker__title">选择上课时间</div>
        <div class="schedule-picker__subtitle">可同时选择多个周几与节次组合</div>
      </div>
      <el-tag type="primary" effect="plain">已选 {{ selectedSlots.length }} 个时间</el-tag>
    </div>

    <div class="schedule-picker__summary">
      {{ scheduleSummary || '尚未选择上课时间' }}
    </div>

    <div class="schedule-picker__grid">
      <div class="schedule-picker__corner">节次/星期</div>
      <div
        v-for="day in WEEK_DAYS"
        :key="day.value"
        class="schedule-picker__header"
      >
        {{ day.label }}
      </div>

      <template v-for="period in PERIOD_OPTIONS" :key="period.value">
        <div class="schedule-picker__period">
          <strong>{{ period.label }}</strong>
          <span>{{ period.time }}</span>
          <small>{{ period.block }}</small>
        </div>
        <button
          v-for="day in WEEK_DAYS"
          :key="`${day.value}-${period.value}`"
          type="button"
          class="schedule-picker__cell"
          :class="{ 'is-active': isSelected(day.value, period.value) }"
          @click="toggleSlot(day.value, period.value)"
        >
          <span>{{ isSelected(day.value, period.value) ? '已选' : '选择' }}</span>
        </button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import {
  PERIOD_OPTIONS,
  WEEK_DAYS,
  buildScheduleSlotKey,
  formatScheduleSlots,
  isCanonicalScheduleValue,
  parseScheduleValue,
  serializeScheduleSlots
} from '@/utils/courseSchedule'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const selectedSlots = ref(parseScheduleValue(props.modelValue))

watch(
  () => props.modelValue,
  value => {
    selectedSlots.value = parseScheduleValue(value)
  }
)

const legacyValue = computed(() => {
  if (!props.modelValue) {
    return ''
  }

  return isCanonicalScheduleValue(props.modelValue) ? '' : props.modelValue
})

const scheduleSummary = computed(() => formatScheduleSlots(selectedSlots.value))

const isSelected = (dayValue, periodValue) =>
  selectedSlots.value.includes(buildScheduleSlotKey(dayValue, periodValue))

const toggleSlot = (dayValue, periodValue) => {
  const slotKey = buildScheduleSlotKey(dayValue, periodValue)

  if (selectedSlots.value.includes(slotKey)) {
    selectedSlots.value = selectedSlots.value.filter(item => item !== slotKey)
  } else {
    selectedSlots.value = [...selectedSlots.value, slotKey]
  }

  emit('update:modelValue', serializeScheduleSlots(selectedSlots.value))
}
</script>

<style scoped>
.schedule-picker {
  width: 100%;
}

.schedule-picker__legacy {
  margin-bottom: 12px;
}

.schedule-picker__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.schedule-picker__title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.schedule-picker__subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.schedule-picker__summary {
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8fafc;
  color: #334155;
  line-height: 1.6;
}

.schedule-picker__grid {
  display: grid;
  grid-template-columns: minmax(148px, 180px) repeat(7, minmax(72px, 1fr));
  border: 1px solid #dbe4f0;
  border-radius: 16px;
  overflow: hidden;
}

.schedule-picker__corner,
.schedule-picker__header {
  padding: 12px 10px;
  background: #eff6ff;
  text-align: center;
  font-weight: 600;
  color: #1d4ed8;
  border-bottom: 1px solid #dbe4f0;
}

.schedule-picker__header:not(:last-child) {
  border-left: 1px solid #dbe4f0;
}

.schedule-picker__period {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  padding: 12px 10px;
  background: #f8fafc;
  border-top: 1px solid #dbe4f0;
}

.schedule-picker__period strong {
  font-size: 13px;
  color: #0f172a;
}

.schedule-picker__period span,
.schedule-picker__period small {
  color: #64748b;
}

.schedule-picker__cell {
  min-height: 78px;
  border: 0;
  border-left: 1px solid #dbe4f0;
  border-top: 1px solid #dbe4f0;
  background: #fff;
  color: #64748b;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.schedule-picker__cell:hover {
  background: #f8fbff;
  color: #1d4ed8;
}

.schedule-picker__cell.is-active {
  background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1d4ed8;
  font-weight: 600;
}

@media (max-width: 900px) {
  .schedule-picker__grid {
    grid-template-columns: minmax(132px, 160px) repeat(7, minmax(60px, 1fr));
    font-size: 12px;
  }

  .schedule-picker__cell {
    min-height: 64px;
  }
}

@media (max-width: 768px) {
  .schedule-picker__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .schedule-picker__grid {
    overflow: auto;
  }
}
</style>
