<template>
  <svg
    class="folder-icon"
    :width="width"
    :height="height"
    viewBox="0 0 40 34"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <defs>
      <!-- 渐变 id 必须每个实例唯一，否则多图标时后面的会渲染成空白 -->
      <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#8FD8FA" />
        <stop offset="1" stop-color="#2F9BEF" />
      </linearGradient>
    </defs>
    <path
      d="M3 7.5C3 5.6 4.6 4 6.5 4h8.1c.9 0 1.7.3 2.3.9l2.3 2.3h14.3C35.4 7.2 37 8.8 37 10.7v16.8c0 1.9-1.6 3.5-3.5 3.5h-27C4.6 31 3 29.4 3 27.5V7.5z"
      :fill="`url(#${gradId})`"
    />
    <path d="M3 12.2h34" stroke="rgba(255,255,255,0.28)" stroke-width="1.2" />
  </svg>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance } from 'vue'

/**
 * 苹果（macOS Big Sur）风格的文件夹图标。
 * 用内联 SVG 而非 emoji 📁：emoji 在 Windows 上是黄色、macOS 上是蓝色，跨平台不一致。
 */
const props = withDefaults(defineProps<{ size?: number }>(), { size: 18 })

const uid = getCurrentInstance()?.uid ?? Math.floor(Math.random() * 1e6)
const gradId = `folderGrad-${uid}`

const width = computed(() => props.size)
const height = computed(() => Math.round((props.size * 34) / 40)) // 宽高比 40:34
</script>

<style scoped>
.folder-icon {
  display: inline-block;
  vertical-align: -0.12em; /* 与文字基线对齐 */
  flex-shrink: 0;
}
</style>
