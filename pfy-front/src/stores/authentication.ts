import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAuthenticationStore = defineStore(
  'authentication',
  () => {
    const pblCd   = ref<string>('');
    const lang    = ref<string>('ko-KR');
    const typeCd  = ref<string>('');
    const compCd  = ref<string>('');
    const userId  = ref<string>('');
    const userName = ref<string>('');

    function setAuth(payload: {
      pblCd?: string;
      lang?: string;
      typeCd?: string;
      compCd?: string;
      userId?: string;
      userName?: string;
    }) {
      if (payload.pblCd   !== undefined) pblCd.value   = payload.pblCd;
      if (payload.lang    !== undefined) lang.value    = payload.lang;
      if (payload.typeCd  !== undefined) typeCd.value  = payload.typeCd;
      if (payload.compCd  !== undefined) compCd.value  = payload.compCd;
      if (payload.userId  !== undefined) userId.value  = payload.userId;
      if (payload.userName !== undefined) userName.value = payload.userName;
    }

    function $reset() {
      pblCd.value    = '';
      lang.value     = 'ko-KR';
      typeCd.value   = '';
      compCd.value   = '';
      userId.value   = '';
      userName.value = '';
    }

    return { pblCd, lang, typeCd, compCd, userId, userName, setAuth, $reset };
  },
  { persist: true }
);
