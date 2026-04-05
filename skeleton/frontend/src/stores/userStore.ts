import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthenticationStore = defineStore('authentication', () => {
  const gPBL_CD = ref('')
  const gLANG = ref('ko')
  const gTYPE_CD = ref('')
  const gCOMP_CD = ref('')

  return { gPBL_CD, gLANG, gTYPE_CD, gCOMP_CD }
})
