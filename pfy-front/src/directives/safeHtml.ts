import DOMPurify from 'dompurify';
import { DirectiveBinding } from 'vue';

import { domPurifyOptions } from '@/utils/domPurifyConfig';

// Safe CSS 옵션 적용
DOMPurify.setConfig({
  SAFE_FOR_TEMPLATES: false, // 템플릿 내 안전성 향상 옵션
  ALLOWED_URI_REGEXP: /^https?:\/\//i, // 허용할 URL 패턴: http 또는 https 로 시작하는 URL만 허용
});

export default {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const html = binding.value?.html ?? binding.value ?? '';
    const options = binding.value?.options ?? domPurifyOptions;
    // eslint-disable-next-line no-param-reassign
    el.innerHTML = DOMPurify.sanitize(html, options).toString();
  },
  updated(el: HTMLElement, binding: DirectiveBinding) {
    const html = binding.value?.html ?? binding.value ?? '';
    const options = binding.value?.options ?? domPurifyOptions;
    // eslint-disable-next-line no-param-reassign
    el.innerHTML = DOMPurify.sanitize(html, options).toString();
  },
};
