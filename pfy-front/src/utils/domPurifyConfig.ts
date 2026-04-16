export const domPurifyOptions = {
  // 사용자가 입력한 HTML에서 허용할 태그 목록
  ALLOWED_TAGS: [
    'b',
    'i',
    'u',
    'a',
    'p',
    'br',
    'ul',
    'li',
    'strong',
    'em',
    'span',
    'div',
    'table',
    'thead',
    'tbody',
    'tr',
    'td',
    'th',
    'blockquote',
    'pre',
    'code',
    'hr',
    'img',
  ],
  // 허용할 속성 목록
  ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'title', 'class'],
  // data-로 시작하는 커스텀 데이터 속성을 허용하지 않음
  ALLOW_DATA_ATTR: false,
  // 절대 허용하지 않을 태그 목록
  FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'link'],
  // 절대 허용하지 않을 속성 목록
  FORBID_ATTR: ['onerror', 'onclick', 'onload', 'style'],
  // 템플릿 내 안전성 향상시키는 옵션
  SAFE_FOR_TEMPLATES: true,
};
