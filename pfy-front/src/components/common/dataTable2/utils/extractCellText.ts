// 요소가 화면에 보이는지 확인하는 헬퍼 함수
const isElementVisible = (element: Element): boolean => {
  const htmlElement = element as HTMLElement;
  const style = window.getComputedStyle(htmlElement);

  return (
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    style.opacity !== '0' &&
    htmlElement.offsetWidth > 0 &&
    htmlElement.offsetHeight > 0
  );
};

// 보이는 텍스트만 추출하는 함수
const getVisibleTextContent = (element: Element): string => {
  let text = '';

  // 텍스트 노드들을 순회하면서 보이는 것들만 수집
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => {
      const { parentElement } = node;
      if (parentElement && isElementVisible(parentElement)) {
        return NodeFilter.FILTER_ACCEPT;
      }
      return NodeFilter.FILTER_REJECT;
    },
  });

  let node = walker.nextNode();
  while (node) {
    text += node.textContent || '';
    node = walker.nextNode();
  }

  return text.trim();
};

// 셀에서 텍스트를 추출하는 헬퍼 함수
export const extractCellText = (cell: Element): string => {
  // 1차: 보이는 텍스트만 추출
  let textContent = getVisibleTextContent(cell);

  // 2차: textContent가 비어있거나 의미없는 경우 다른 방법 시도
  if (!textContent || textContent === '—' || textContent === '-') {
    // input 요소들의 값 확인 (보이는 것만)
    const inputs = cell.querySelectorAll('input, textarea, select');
    for (let i = 0; i < inputs.length; i += 1) {
      const input = inputs[i];
      if (isElementVisible(input)) {
        const value = (input as HTMLInputElement).value?.trim();
        if (value) {
          textContent = value;
          break;
        }
      }
    }

    // data 속성 확인 (셀 자체가 보이는 경우에만)
    if (!textContent && isElementVisible(cell)) {
      const dataValue =
        cell.getAttribute('data-value') ||
        cell.getAttribute('data-text') ||
        cell.getAttribute('title');
      if (dataValue) {
        textContent = dataValue.trim();
      }
    }

    // 특정 클래스나 속성을 가진 요소의 텍스트 확인 (보이는 것만)
    if (!textContent) {
      const valueElements = cell.querySelectorAll(
        '[data-value], .cell-value, .display-value'
      );
      for (let j = 0; j < valueElements.length; j += 1) {
        const valueElement = valueElements[j];
        if (isElementVisible(valueElement)) {
          const elementText = valueElement.textContent?.trim();
          if (elementText) {
            textContent = elementText;
            break;
          }
        }
      }
    }

    // 마지막 수단: innerText 사용 (이미 보이는 텍스트만 반환함)
    if (!textContent && 'innerText' in cell && isElementVisible(cell)) {
      textContent = (cell as HTMLElement).innerText?.trim() || '';
    }
  }

  return textContent;
};
