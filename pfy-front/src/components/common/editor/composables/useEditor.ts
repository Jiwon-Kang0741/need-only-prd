import { Color } from '@tiptap/extension-color';
import { Table } from '@tiptap/extension-table';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { TableRow } from '@tiptap/extension-table-row';
import { TaskItem } from '@tiptap/extension-task-item';
import { TaskList } from '@tiptap/extension-task-list';
import { TextAlign } from '@tiptap/extension-text-align';
import { TextStyle } from '@tiptap/extension-text-style';
import StarterKit from '@tiptap/starter-kit';
import { type Editor, useEditor } from '@tiptap/vue-3';
import { onBeforeUnmount, type ShallowRef } from 'vue';

type TextStyleType = 'bold' | 'underline' | 'italic';
type Align = 'left' | 'center' | 'right' | 'justify';
type TableCmd =
  | 'insertTable'
  | 'addColumnBefore'
  | 'addColumnAfter'
  | 'deleteColumn'
  | 'addRowBefore'
  | 'addRowAfter'
  | 'deleteRow'
  | 'mergeCells'
  | 'splitCell';

type EditorRef = ShallowRef<Editor | undefined>;

type InsertTableOptions = {
  rows?: number;
  cols?: number;
  withHeaderRow?: boolean;
};

type EditorUtils = {
  getHTML: () => string;
  getJSON: () => any;
  setHTML: (html: string) => void;
  setJSON: (json: any) => void;
  getText: () => string;
};

// 유효 레벨 상수/정제 함수
export const LEVELS = [1, 2, 3, 4, 5, 6] as const;
export type Level = (typeof LEVELS)[number];

// 커스텀 테이블 스타일을 위한 확장
const CustomTable = Table.extend({
  addOptions() {
    return {
      ...this.parent?.(),
      resizable: true,
      cellMinWidth: 50,
      allowTableNodeSelection: true,
    };
  },
});

const CustomTableRow = TableRow.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      style: {
        default: null,
        parseHTML: (element) => element.getAttribute('style'),
        renderHTML: (attributes) => {
          if (!attributes.style) return {};
          return {
            style: attributes.style,
          };
        },
      },
    };
  },
});

const CustomTableCell = TableCell.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      style: {
        default: null, // ✅ 기본값은 null
        parseHTML: (element) => element.getAttribute('style'),
        renderHTML: (attributes) => {
          return attributes.style
            ? { style: attributes.style } // 기존 스타일 유지
            : {
                // ✅ fallback 스타일 (style 없을 때만)
                style:
                  'border: 1px solid #d2d7df; box-sizing: border-box; min-width: 1em; padding: 6px 8px; position: relative; vertical-align: top;',
              };
        },
      },
    };
  },
});

const CustomTableHeader = TableHeader.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      style: {
        default: null, // ✅ 기본값은 null
        parseHTML: (element) => element.getAttribute('style'),
        renderHTML: (attributes) => {
          return attributes.style
            ? { style: attributes.style } // 기존 스타일 유지
            : {
                // ✅ fallback 스타일
                style:
                  'border: 1px solid #d2d7df; box-sizing: border-box; min-width: 5em; padding: 6px 8px; position: relative; vertical-align: top; background-color: #f4f6fa; font-weight: bold; text-align: left;',
              };
        },
      },
    };
  },
});
export function useTiptapEditor(initialContent = '') {
  const editor = useEditor({
    content: initialContent,
    extensions: [
      StarterKit,
      // CustomHeading.configure({ levels: [1, 2, 3] }),
      TextStyle,
      Color.configure({
        types: ['textStyle'], // 어떤 노드/마크에 색상을 적용할지
      }),
      CustomTable,
      CustomTableRow,
      CustomTableCell,
      CustomTableHeader,
      TaskList,
      // Text, // StarterKit에 포함되어 있지만 유지해도 무방
      TaskItem.configure({ nested: true }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }), // 텍스트 정렬
      // Underline,
    ],
  }) as EditorRef;

  // 언마운트 시 정리
  onBeforeUnmount(() => {
    editor.value?.destroy();
  });

  /** 공통 가드: editor.value가 있을 때만 실행 */
  const withEditor =
    <T extends unknown[]>(fn: (e: Editor, ...args: T) => void) =>
    (...args: T) => {
      const e = editor.value;
      if (!e) return;
      fn(e, ...args);
    };

  /** -------- Commands -------- */
  const commands = {
    /** 텍스트 정렬 */
    setTextAlign: withEditor((e, dir: Align) =>
      e.chain().focus().setTextAlign(dir).run()
    ),
    /** Bold / Italic */
    toggleBold: withEditor((e) => e.chain().focus().toggleBold().run()),
    toggleUnderline: withEditor((e) =>
      e.chain().focus().toggleUnderline().run()
    ),
    toggleItalic: withEditor((e) => e.chain().focus().toggleItalic().run()),
    toggleBlockquote: withEditor((e) =>
      e.chain().focus().toggleBlockquote().run()
    ),
    /** Task List / Bullet / Ordered / Paragraph */
    toggleTaskList: withEditor((e) => e.chain().focus().toggleTaskList().run()),
    toggleBulletList: withEditor((e) =>
      e.chain().focus().toggleBulletList().run()
    ),
    toggleOrderedList: withEditor((e) =>
      e.chain().focus().toggleOrderedList().run()
    ),
    /** Heading 및 Paragraph 설정 */
    setHeading: withEditor((e, level: Level = 1 as Level) => {
      e.chain().focus().setHeading({ level }).run();
    }),
    setParagraph: withEditor((e) => e.chain().focus().setParagraph().run()),
    /** 테이블 생성 */
    insertTable: withEditor((e, opts: InsertTableOptions = {}) => {
      const { rows = 3, cols = 3, withHeaderRow = true } = opts;
      e.chain().focus().insertTable({ rows, cols, withHeaderRow }).run();
    }),
    /** 테이블 조작 */
    addColumnBefore: withEditor((e) =>
      e.chain().focus().addColumnBefore().run()
    ),
    addColumnAfter: withEditor((e) => e.chain().focus().addColumnAfter().run()),
    deleteColumn: withEditor((e) => e.chain().focus().deleteColumn().run()),
    addRowBefore: withEditor((e) => e.chain().focus().addRowBefore().run()),
    addRowAfter: withEditor((e) => e.chain().focus().addRowAfter().run()),
    deleteRow: withEditor((e) => e.chain().focus().deleteRow().run()),
    mergeCells: withEditor((e) => e.chain().focus().mergeCells().run()),
    splitCell: withEditor((e) => e.chain().focus().splitCell().run()),
    /** Undo / Redo */
    undo: withEditor((e) => e.chain().focus().undo().run()),
    redo: withEditor((e) => e.chain().focus().redo().run()),
    setColor: (color: string) =>
      withEditor((e) => e.chain().focus().setColor(color).run()),
    clearColor: () => withEditor((e) => e.chain().focus().unsetColor().run()),
  };

  /** -------- can() helpers (버튼 활성/비활성 제어) -------- */
  const can = {
    insertTable: (rows = 3, cols = 3, withHeaderRow = true) =>
      !!editor.value
        ?.can()
        .chain()
        .focus()
        .insertTable({ rows, cols, withHeaderRow })
        .run(),
    addColumnBefore: () =>
      !!editor.value?.can().chain().focus().addColumnBefore().run(),
    addColumnAfter: () =>
      !!editor.value?.can().chain().focus().addColumnAfter().run(),
    deleteColumn: () =>
      !!editor.value?.can().chain().focus().deleteColumn().run(),
    addRowBefore: () =>
      !!editor.value?.can().chain().focus().addRowBefore().run(),
    addRowAfter: () =>
      !!editor.value?.can().chain().focus().addRowAfter().run(),
    deleteRow: () => !!editor.value?.can().chain().focus().deleteRow().run(),
    mergeCells: () => !!editor.value?.can().chain().focus().mergeCells().run(),
    splitCell: () => !!editor.value?.can().chain().focus().splitCell().run(),
    undo: () => !!editor.value?.can().chain().focus().undo().run(),
    redo: () => !!editor.value?.can().chain().focus().redo().run(),
  };

  /** -------- isActive helpers (UI 상태 표시) -------- */
  const isActive = {
    textStyle: (style: TextStyleType) => editor.value?.isActive(style) ?? false,
    blockquote: () => editor.value?.isActive('blockquote') ?? false,
    taskList: () => editor.value?.isActive('taskList') ?? false,
    bulletList: () => editor.value?.isActive('bulletList') ?? false,
    orderedList: () => editor.value?.isActive('orderedList') ?? false,
    paragraph: () => editor.value?.isActive('paragraph') ?? false,
    heading: (level: number) =>
      editor.value?.isActive('heading', { level }) ?? false,
    textAlign: (dir: Align) =>
      editor.value?.isActive({ textAlign: dir }) ?? false,
    // 표 내부 여부 등도 필요하면 추가:
    inTable: () => editor.value?.isActive('table') ?? false,
    color: (color: string) =>
      editor.value?.isActive('textStyle', { color }) ?? false,
  };

  const TextStyleRunMap: Record<TextStyleType, () => void> = {
    bold: () => commands.toggleBold(),
    underline: () => commands.toggleUnderline(),
    italic: () => commands.toggleItalic(),
  };

  /** (선택) 테이블 전용 런타임 맵: 버튼에서 바로 호출하고 싶을 때 */
  const tableRunMap: Record<TableCmd, () => void> = {
    insertTable: () => commands.insertTable(),
    addColumnBefore: () => commands.addColumnBefore(),
    addColumnAfter: () => commands.addColumnAfter(),
    deleteColumn: () => commands.deleteColumn(),
    addRowBefore: () => commands.addRowBefore(),
    addRowAfter: () => commands.addRowAfter(),
    deleteRow: () => commands.deleteRow(),
    mergeCells: () => commands.mergeCells(),
    splitCell: () => commands.splitCell(),
  };

  const tableCanMap: Record<TableCmd, () => boolean> = {
    insertTable: () => can.insertTable(),
    addColumnBefore: () => can.addColumnBefore(),
    addColumnAfter: () => can.addColumnAfter(),
    deleteColumn: () => can.deleteColumn(),
    addRowBefore: () => can.addRowBefore(),
    addRowAfter: () => can.addRowAfter(),
    deleteRow: () => can.deleteRow(),
    mergeCells: () => can.mergeCells(),
    splitCell: () => can.splitCell(),
  };

  // 저장, 불러오기 기능
  const utils = {
    getHTML: () => editor.value?.getHTML() ?? '',
    getJSON: () => editor.value?.getJSON() ?? {},
    getText: () => editor.value?.getText() ?? '',

    setHTML: (html: string) =>
      editor.value?.commands.setContent(html, { emitUpdate: true }), // false - Undo/Redo 기록 스택에 해당 변경 사항을 저장하지 않는다
    setJSON: (json: any) =>
      editor.value?.commands.setContent(json, { emitUpdate: true }), // false - Undo/Redo 기록 스택에 해당 변경 사항을 저장하지 않는다
  } as EditorUtils;

  return {
    editor, // 에디터 인스턴스 - ShallowRef<Editor | undefined>
    commands, // 실행 커맨드
    can, // 가능 여부(버튼 disabled 제어)
    isActive, // UI 상태(활성/선택 표시)
    TextStyleRunMap, // text style 기능 맵
    tableRunMap, // 테이블 기능 맵
    tableCanMap, // 테이블 액션 버튼 활성화/비활성화 맵
    utils, // 저장, 불러오기 액션
  };
}
