/**
 * stripInterviewSidePanel
 *
 * generate.ts 가 삽입한 마커를 기준으로, spec-source/Component.vue 저장 시
 * 인터뷰 전용 사이드 패널 영역(템플릿/스크립트/CSS)을 제거한다.
 *
 * 마커 구조:
 *  [template open wrapper]
 *    <!-- [interview-side:template-open] -->
 *    <div class="gp-page-split"><div class="gp-page-split__main">
 *    → 마커+래퍼 태그 제거, 내부 콘텐츠 언랩
 *
 *  [template close+aside]
 *    <!-- [interview-side:template-close] --> ... <!-- [interview-side:template-close-end] -->
 *    → 블록 전체 제거
 *
 *  [script]
 *    /* [interview-side:script-start] * / ... /* [interview-side:script-end] * /
 *    → 블록 전체 제거
 *
 *  [css]
 *    /* [interview-side:css-start] * / ... /* [interview-side:css-end] * /
 *    → 블록 전체 제거
 */

const TEMPLATE_OPEN_MARKER  = '<!-- [interview-side:template-open] -->';
const TEMPLATE_CLOSE_START  = '<!-- [interview-side:template-close] -->';
const TEMPLATE_CLOSE_END    = '<!-- [interview-side:template-close-end] -->';
const SCRIPT_START          = '/* [interview-side:script-start] */';
const SCRIPT_END            = '/* [interview-side:script-end] */';
const CSS_START             = '/* [interview-side:css-start] */';
const CSS_END               = '/* [interview-side:css-end] */';

/** 마커 사이 블록 전체 제거 (startMarker ~ endMarker 포함) */
function removeBlock(source: string, startMarker: string, endMarker: string): string {
  const start = source.indexOf(startMarker);
  const end   = source.indexOf(endMarker);
  if (start === -1 || end === -1 || end < start) return source;
  return source.slice(0, start) + source.slice(end + endMarker.length);
}

/** template open 래퍼 언랩
 *  <!-- [interview-side:template-open] -->
 *  <div class="gp-page-split">
 *    <div class="gp-page-split__main">
 *  → 세 줄 모두 제거 (내부 콘텐츠는 유지)
 */
function removeTemplateOpenWrapper(source: string): string {
  const markerIdx = source.indexOf(TEMPLATE_OPEN_MARKER);
  if (markerIdx === -1) return source;

  // 마커 이후 줄들에서 gp-page-split / gp-page-split__main 래퍼 태그 제거
  let result = source;
  result = result.replace(TEMPLATE_OPEN_MARKER, '');
  result = result.replace(/[ \t]*<div class="gp-page-split">\n?/, '');
  result = result.replace(/[ \t]*<div class="gp-page-split__main">\n?/, '');
  return result;
}

export function stripInterviewSidePanel(source: string): string {
  let result = source;

  // 1. template close+aside 블록 제거 (</div> + <aside>...</aside> + </div>)
  result = removeBlock(result, TEMPLATE_CLOSE_START, TEMPLATE_CLOSE_END);

  // 2. template open 래퍼 언랩 (split layout 제거)
  result = removeTemplateOpenWrapper(result);

  // 3. script 인터뷰 블록 제거
  result = removeBlock(result, SCRIPT_START, SCRIPT_END);

  // 4. CSS 인터뷰 블록 제거
  result = removeBlock(result, CSS_START, CSS_END);

  // 5. 연속 빈 줄 정리 (3줄 이상 → 2줄)
  result = result.replace(/\n{3,}/g, '\n\n');

  return result;
}
