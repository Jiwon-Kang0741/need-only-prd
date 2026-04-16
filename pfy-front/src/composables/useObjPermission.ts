import { ref } from 'vue';

export type IsBlockedFn = (objId: string) => boolean;

export function useObjPermission(_windowId: string) {
  const blockList = ref<string[]>([]);

  const isBlocked: IsBlockedFn = (objId) => {
    if (!objId) return false;
    return blockList.value.includes(objId);
  };

  return { isBlocked };
}
