// /constants/guideMenu.ts

export interface GuideComponentMeta {
  label: string;
  componentName: string;
}

// 가이드 컴포넌트 목록 (알파벳 순으로 정렬)
const guideComponents = [
  'BadgeGuide',
  'BreadcrumbGuide',
  'ButtonGuide',
  'ChartGuide',
  'CheckboxGuide',
  'ChipGuide',
  'confirmDialogGuide',
  'DataTableGuide',
  'DatePickerGuide',
  'DialogGuide',
  'DotStatusTextGuide',
  'EditorGuide',
  'FullCalendarGuide',
  'IconsGuide',
  'InputNumberGuide',
  'InputOtpGuide',
  'InputTextGuide',
  'MessageGuide',
  'MultiSelectAdvencedGuide',
  'MultiSelectGuide',
  'PasswordGuide',
  'PopoverGuide',
  'RadioButtonGuide',
  'SearchFormGuide',
  'SelectAdvencedGuide',
  'SelectButtonGuide',
  'SelectGuide',
  'SumGridGuide',
  'TabContentGuide',
  'TagGuide',
  'ToastGuide',
  'TreeTableGuide',
  'ToggleButtonGuide',
  'ToggleSwitchGuide',
  'tooltipGuide',
].sort();

// componentName에서 label 생성 함수
function generateLabel(componentName: string): string {
  // 'Guide' 제거
  let label = componentName.replace(/Guide$/i, '');

  // 카멜케이스를 공백으로 분리 (예: MultiSelect -> Multi Select)
  label = label.replace(/([a-z])([A-Z])/g, '$1 $2');

  // 첫 글자 대문자로
  return label.charAt(0).toUpperCase() + label.slice(1);
}

// 자동으로 GuideComponentMeta 배열 생성
export const guideComponentList: GuideComponentMeta[] = guideComponents.map(
  (componentName) => ({
    label: generateLabel(componentName),
    componentName,
  })
);
