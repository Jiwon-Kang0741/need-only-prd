import { defineStore } from 'pinia';

export const useSearchParamStore = defineStore('searchParams', {
  state: () => ({
    paramsByWindow: {} as Record<string, any>,
  }),
  actions: {
    set(windowId: string, params: any) {
      this.paramsByWindow[windowId] = params;
    },
    consume(windowId: string) {
      const params = this.paramsByWindow[windowId];
      delete this.paramsByWindow[windowId];
      return params;
    },
  },
});
