import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { MasterForm, PlatformOverrideSetting, MatrixPreset } from '../types/matrix'
import { createDualStorage } from '../utils/storageAdapter'

const STORAGE_KEY = 'sau_matrix_presets'

const presetStorage = createDualStorage<MatrixPreset[]>({
  diskKey: 'matrix_presets',
  localKey: STORAGE_KEY,
  getDefault: () => [],
  debounceMs: 300,
  transformLoad: (raw) => (Array.isArray(raw) ? raw : [])
})

export function useMatrixPresets(
  masterForm: MasterForm,
  platformOverrides: Record<string, PlatformOverrideSetting>,
  accountOverrides: Record<string, PlatformOverrideSetting>
) {
  const savedTemplates = ref<MatrixPreset[]>(presetStorage.get())

  // 从本地缓存/物理磁盘加载所有预设
  const loadTemplatesFromStorage = async () => {
    await presetStorage.load((synced) => {
      savedTemplates.value = synced
    })
  }

  // 持久化保存 (热缓存即时更新 + 磁盘原子防抖落盘)
  const saveTemplatesToStorage = () => {
    presetStorage.save(savedTemplates.value)
  }

  // 处理下拉菜单指令
  const handleTemplateCommand = (cmd: string) => {
    if (cmd === 'save') {
      ElMessageBox.prompt('请输入预设模板名称 (如: 数码科技全矩阵精细化模板)', '存为预设模板', {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        inputPattern: /\S+/,
        inputErrorMessage: '模板名称不能为空'
      }).then(({ value }) => {
        const preset: MatrixPreset = {
          id: String(Date.now()),
          name: value.trim(),
          createdAt: new Date().toLocaleDateString(),
          master: JSON.parse(JSON.stringify(masterForm)),
          platformOverrides: JSON.parse(JSON.stringify(platformOverrides)),
          accountOverrides: JSON.parse(JSON.stringify(accountOverrides))
        }
        savedTemplates.value.push(preset)
        saveTemplatesToStorage()
        ElMessage.success(`预设模板「${value.trim()}」已成功保存`)
      }).catch(() => {})
    } else if (cmd === 'clear') {
      savedTemplates.value = []
      saveTemplatesToStorage()
      ElMessage.success('已清空所有预设模板')
    } else if (cmd.startsWith('load:')) {
      const id = cmd.replace('load:', '')
      const found = savedTemplates.value.find(t => t.id === id)
      if (found) {
        Object.assign(masterForm, JSON.parse(JSON.stringify(found.master)))
        Object.assign(platformOverrides, JSON.parse(JSON.stringify(found.platformOverrides || (found as any).overrides || {})))
        if (found.accountOverrides) {
          Object.assign(accountOverrides, JSON.parse(JSON.stringify(found.accountOverrides)))
        }
        ElMessage.success(`已加载预设模板「${found.name}」`)
      }
    }
  }

  return {
    savedTemplates,
    loadTemplatesFromStorage,
    saveTemplatesToStorage,
    handleTemplateCommand
  }
}
