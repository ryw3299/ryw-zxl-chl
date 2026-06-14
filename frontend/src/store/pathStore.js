import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPaths, generatePath, getPathDetail } from '@/api/path'

export const usePathStore = defineStore('path', () => {
  const paths = ref([])
  const currentPath = ref(null)
  const loading = ref(false)

  async function fetchPaths() {
    paths.value = await getPaths()
  }

  async function generate(params) {
    loading.value = true
    try {
      currentPath.value = await generatePath(params)
      await fetchPaths()
      return currentPath.value
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id) {
    loading.value = true
    try {
      currentPath.value = await getPathDetail(id)
      return currentPath.value
    } finally {
      loading.value = false
    }
  }

  return { paths, currentPath, loading, fetchPaths, generate, fetchDetail }
})
