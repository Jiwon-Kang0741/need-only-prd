export interface UiObject {
  objtTypeCd: string;
  objtId: string;
  objtNm?: string;
}

/**
 * DOM 내 [data-object-id] 속성을 가진 엘리먼트들을 탐색하여
 * UI 오브젝트 배열로 변환하는 함수
 *
 * @param container 탐색할 DOM 컨테이너, 기본값은 document 전체
 * @returns UiObject 배열
 */
export function extractDomObjects(
  container: HTMLElement | Document = document
): UiObject[] {
  const objects: UiObject[] = [];

  /**
   * 공통 오브젝트 생성 함수
   * - objectId가 'app'이 아니고 유효할 경우에만 객체 생성
   * - 타입에 따라 text 속성 포함
   *   (버튼(btn), 스태틱 텍스트(sta), 그리드(grd, 여러개일 경우 grdMain, grdSub), 체크박스(chk), 탭(tab))
   * - 렌더링 되는 요소에 대해서만 오브젝트 추출이 가능함
   */
  const processElement = (
    objtTypeCd: string,
    el: HTMLElement,
    objtId: string
  ) => {
    if (objtId && objtId !== 'app') {
      const obj: UiObject = { objtTypeCd, objtId };

      // text가 필요한 타입에 한해 텍스트 내용 추출
      if (
        ['Button', 'Static', 'Grid', 'Checkbox', 'Tab'].includes(objtTypeCd)
      ) {
        obj.objtNm = el.textContent?.trim() ?? '';
      }

      objects.push(obj);
    }
  };

  // container 내 모든 data-object-id 속성을 가진 요소 순회
  container.querySelectorAll('[data-object-id]').forEach((el) => {
    if (el.getAttribute('data-extract-skip') === 'true') return; // Excel Upload, Download 등 다국어관리 하지 않는 필드에 추가하면 해당 필드 스킵함.
    const tag = el.tagName.toLowerCase();
    const objtId = el.getAttribute('data-object-id') || '';

    if (!objtId) return;

    // 체크박스 input은 Checkbox 타입으로 분류
    if (
      (tag === 'input' && (el as HTMLInputElement).type === 'checkbox') ||
      (tag === 'div' && el.classList.contains('p-checkbox')) ||
      (objtId && objtId.startsWith('chk'))
    ) {
      processElement('Checkbox', el as HTMLElement, objtId);
      // button, li 태그는 objectId 패턴에 따라 Tab 혹은 Button 타입으로 분기
    } else if (tag === 'button' || tag === 'li') {
      if (/^[A-Za-z0-9]+\.tab[A-Za-z0-9_]*$/.test(objtId)) {
        // ex) myapp.tab1, main.tab_abc 등 탭 식별용 패턴
        processElement('Tab', el as HTMLElement, objtId);
      } else {
        processElement('Button', el as HTMLElement, objtId);
      }
      // div, span, strong, a, label 태그는 Grid 패턴 또는 Static 텍스트로 분기
    } else if (['div', 'span', 'strong', 'a', 'label'].includes(tag)) {
      if (/grd[A-Za-z0-9_]*\..+$/.test(objtId)) {
        // ex) DSOV010.grdMain.col1, DSOV020.grdSub.col1 등 그리드 식별용 패턴
        processElement('Grid', el as HTMLElement, objtId);
      } else {
        // 위 패턴이 아니면 일반 텍스트 요소로 간주
        processElement('Static', el as HTMLElement, objtId);
      }
    }
  });

  return objects;
}

/**
 * DOM 내 [data-object-id] 속성을 가진 버튼(btn)만 탐색하여
 * UI 오브젝트 배열로 변환하는 함수
 *
 * @param container 탐색할 DOM 컨테이너, 기본값은 document 전체
 * @returns UiObject 배열 (Button만 포함)
 */
export const extractBtnDomObjects = (
  container: HTMLElement | Document = document
): UiObject[] => {
  const objects: UiObject[] = [];

  const processButton = (el: HTMLElement, objtId: string) => {
    if (objtId && objtId !== 'app') {
      const obj: UiObject = {
        objtTypeCd: 'Button',
        objtId,
        objtNm: el.textContent?.trim() ?? '',
      };
      objects.push(obj);
    }
  };

  container.querySelectorAll('[data-object-id]').forEach((el) => {
    // 다국어관리는 해야하지만 프론트 상 자체 로직이 들어가는 버튼의 경우 권한 관리 X , 해당 필드 스킵(화면관리 오브젝트 추출)
    if (el.getAttribute('data-extract-skip-btn') === 'true') return;
    const tag = el.tagName.toLowerCase();
    const objtId = el.getAttribute('data-object-id') || '';

    if (!objtId) return;

    // btn으로 시작하거나 button 태그인 경우만 추출
    if (tag === 'button' || objtId.startsWith('btn')) {
      processButton(el as HTMLElement, objtId);
    }
  });

  return objects;
};
