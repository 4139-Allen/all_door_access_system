<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] }
})

const chartRef = ref(null)
let chart = null

const colors = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

const renderChart = () => {
  if (!chartRef.value || !props.data.length) return

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 次 ({d}%)'
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#6b7280' },
      // 图例显示：名称 + 次数 + 百分比
      formatter: (name) => {
        const item = props.data.find(d => d.name === name)
        if (!item) return name
        const total = props.data.reduce((s, d) => s + d.value, 0)
        const pct = total > 0 ? ((item.value / total) * 100).toFixed(0) : 0
        return `${name} ${item.value}次（${pct}%）`
      }
    },
    color: colors,
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 12 },
      data: props.data
    }]
  })
}

watch(() => props.data, renderChart, { deep: true })
onMounted(() => {
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})
onUnmounted(() => {
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.chart-container {
  height: 260px;
}
</style>
