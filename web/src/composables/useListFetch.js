import { ref, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

/**
 * 通用分页列表获取 composable
 *
 * @param {string} url - API 路径
 * @param {object} options
 * @param {object} options.defaultFilter - 默认筛选条件
 * @param {number} options.initialPage - 起始页码
 * @param {number} options.initialSize - 每页条数
 * @param {boolean} options.immediate - 是否在 onMounted 时自动请求
 * @param {function} options.paramsBuilder - 将 filterForm 转为请求参数的函数
 */
export function useListFetch(url, {
  defaultFilter = {},
  initialPage = 1,
  initialSize = 10,
  immediate = true,
  paramsBuilder = null,
} = {}) {
  const page = ref(initialPage)
  const size = ref(initialSize)
  const total = ref(0)
  const loading = ref(false)
  const dataList = ref([])
  const filterForm = ref({ ...defaultFilter })

  let abortController = null
  let unmounted = false

  function abort() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }

  async function fetchData() {
    // 取消上一次未完成的请求，防止竞态
    abort()

    const controller = new AbortController()
    abortController = controller

    loading.value = true
    try {
      const params = { page: page.value, size: size.value }
      if (paramsBuilder) {
        Object.assign(params, paramsBuilder(filterForm.value))
      }
      const res = await request.get(url, { params, signal: controller.signal })
      if (unmounted) return
      if (!res.success) {
        ElMessage.error(res.msg || '请求失败')
        return
      }
      dataList.value = res.data?.list || []
      total.value = res.data?.total || 0
    } catch (e) {
      // 组件已卸载或被主动取消的请求不处理
      if (unmounted || e?.name === 'CanceledError') return
      console.error(`[useListFetch] ${url}`, e)
    } finally {
      if (!unmounted) loading.value = false
    }
  }

  watch([page, size], fetchData)

  function resetPageAndSearch() {
    page.value = 1
    fetchData()
  }

  function resetFilter() {
    filterForm.value = { ...defaultFilter }
    page.value = 1
    fetchData()
  }

  if (immediate) {
    onMounted(fetchData)
  }

  onUnmounted(() => {
    unmounted = true
    abort()
  })

  return {
    page,
    size,
    total,
    loading,
    dataList,
    filterForm,
    fetchData,
    resetPageAndSearch,
    resetFilter,
  }
}
