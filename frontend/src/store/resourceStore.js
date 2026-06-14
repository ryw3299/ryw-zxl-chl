import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getResources, getResourceDetail } from '@/api/resource'
import {
  generateResource as genResourceApi,
  getGeneratedResources,
  getGeneratedResourceDetail,
} from '@/api/generatedResource'

export const useResourceStore = defineStore('resource', () => {
  const resources = ref([])
  const total = ref(0)
  const currentResource = ref(null)
  const generatedResources = ref([])
  const loading = ref(false)
  const filters = ref({
    resource_type: '', direction: '', difficulty: '',
    keyword: '', page: 1, page_size: 20,
  })

  async function fetchResources(params) {
    loading.value = true
    try {
      Object.assign(filters.value, params || {})
      const res = await getResources(filters.value)
      resources.value = res.items || []
      total.value = res.total || 0
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    loading.value = true
    try {
      currentResource.value = await getResourceDetail(id)
      return currentResource.value
    } finally {
      loading.value = false
    }
  }

  async function generate(params) {
    loading.value = true
    try {
      const res = await genResourceApi(params)
      await fetchGenerated()
      return res
    } finally {
      loading.value = false
    }
  }

  async function fetchGenerated() {
    generatedResources.value = await getGeneratedResources()
  }

  return {
    resources, total, currentResource, generatedResources, loading, filters,
    fetchResources, fetchDetail, generate, fetchGenerated,
  }
})
