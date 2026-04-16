import type { ConfirmationOptions } from 'primevue/confirmationoptions';
import { useConfirm } from 'primevue/useconfirm';

export interface ExtendedConfirmationOptions extends ConfirmationOptions {
  extraActions?: { label: string; onClick: () => void; icon?: string }[];
}

export function useConfirmDialog() {
  const confirmService = useConfirm();

  function confirm(options: ExtendedConfirmationOptions) {
    confirmService.require({
      ...options,
    });
  }

  function closeConfirm() {
    confirmService.close();
  }

  return {
    confirm,
    closeConfirm,
  };
}
