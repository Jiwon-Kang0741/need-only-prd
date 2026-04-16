import { getMsg } from '@/api/message';
import { useConfirmDialog } from '@/composables/useConfirmDialog';
import { useToastMessage } from '@/composables/useToastMessage';

/**
 *  import { useMsg } from '@/composables/useMessage';
 *  const { msg, msgToast, msgConfirm, getMsgNm } = useMsg(); *
 *  toast 메시지 (서버 messageType 에 따라 자동 분기, MsgOptions 옵션도 사용 가능) -> await msg('CM0001'); *
 *  toast 메시지 (토스트만)-> await msgToast('CM0001'); 또는 await msgToast('CM0022', [args, args], { severity: 'warn' })*
 *  Confirm 다이얼로그 ->  await msgConfirm('CM0003', ['홍길동']);
 *  메시지 문구만 반환 ->  await getMsgNm('MO7001');
 *  */

type Arg = string | number;
type Severity = 'success' | 'info' | 'warn' | 'error';

// 대문자/트림 정규화
const normalizeType = (t?: string) => (t ?? '').toString().trim().toUpperCase();

// D 기본 /Q 문의/ W 경고/ I 안내
const mapTypeToSeverity = (t?: string): Severity => {
  switch (normalizeType(t)) {
    case 'D':
    case 'I':
      return 'info';
    case 'W':
      return 'warn';
    case 'Q':
      return 'info';
    case 'E':
      return 'error';
    case 'S':
      return 'success';
    default:
      return 'info';
  }
};

/** 문구만 필요할 때 (messageName만 반환) */
export async function getMsgNm(
  msgId: string,
  msgArgs: Arg[] = []
): Promise<string> {
  const { messageName } = await getMsg({ msgId, msgArgs });
  return messageName;
}

export interface MsgOptions {
  life?: number;
  header?: string;
  acceptLabel?: string;
  rejectLabel?: string;
  severity?: Severity;
}

export function useMsg() {
  const { confirm } = useConfirmDialog();
  const { toast } = useToastMessage();

  /** 서버 messageType에 따라 자동 분기 (Q/CONFIRM → Confirm, 그 외 → Toast) */
  async function msg(
    msgId: string,
    msgArgs: Arg[] = [],
    opt: MsgOptions = {}
  ): Promise<boolean> {
    const { messageType, messageName } = await getMsg({ msgId, msgArgs });
    const t = normalizeType(messageType);

    if (t === 'Q' || t === 'CONFIRM') {
      const [headerText, okText, cancelText] = await Promise.all([
        opt.header ? Promise.resolve(opt.header) : getMsgNm('MO7001'), // 예: "확인"
        opt.acceptLabel ? Promise.resolve(opt.acceptLabel) : getMsgNm('MO7001'),
        opt.rejectLabel ? Promise.resolve(opt.rejectLabel) : getMsgNm('MO7002'), // 예: "취소"
      ]);

      return new Promise<boolean>((resolve) => {
        confirm({
          message: messageName,
          header: headerText,
          acceptLabel: okText,
          rejectLabel: cancelText,
          accept: () => resolve(true),
          reject: () => resolve(false),
          onHide: () => resolve(false),
        });
      });
    }

    toast({
      summary: messageName,
      severity: opt.severity ?? mapTypeToSeverity(t),
      life: opt.life ?? 3000,
    });
    return true;
  }

  async function msgToast(
    msgId: string,
    msgArgs: Arg[] = [],
    opt: MsgOptions = {}
  ): Promise<void> {
    const { messageName, messageType } = await getMsg({ msgId, msgArgs });
    const t = normalizeType(messageType);
    toast({
      summary: messageName,
      severity: opt.severity ?? mapTypeToSeverity(t),
      life: opt.life ?? 3000,
    });
  }

  /** 무조건 Confirm (라벨도 메시지에서 받아오기) */
  async function msgConfirm(
    msgId: string,
    msgArgs: Arg[] = [],
    opt: MsgOptions = {}
  ): Promise<boolean> {
    const { messageName } = await getMsg({ msgId, msgArgs });
    const [headerText, okText, cancelText] = await Promise.all([
      opt.header ? Promise.resolve(opt.header) : getMsgNm('MO7001'),
      opt.acceptLabel ? Promise.resolve(opt.acceptLabel) : getMsgNm('CM0054'),
      opt.rejectLabel ? Promise.resolve(opt.rejectLabel) : getMsgNm('CM0055'),
    ]);

    return new Promise<boolean>((resolve) => {
      confirm({
        message: messageName,
        header: headerText,
        acceptLabel: okText,
        rejectLabel: cancelText,
        accept: () => resolve(true),
        reject: () => resolve(false),
        onHide: () => resolve(false),
      });
    });
  }

  return { msg, msgToast, msgConfirm, getMsgNm };
}
