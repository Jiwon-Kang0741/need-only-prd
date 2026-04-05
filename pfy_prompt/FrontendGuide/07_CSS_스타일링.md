# 07. CSS 스타일링

## 📋 이 단계의 목적

**신규 화면 개발·기존 화면 수정** 시, 기존 화면과 **동일한 톤앤매너와 스타일 가이드**를 따라 일관된 UI를 구현합니다.

- **신규**: 유사 기존 화면(같은 모듈/카테고리 또는 spov010 등)을 참고해 padding·gap·색상 변수·hover/active 효과를 맞춥니다.
- **수정**: 해당 화면의 기존 SCSS·디자인 토큰을 유지하면서 변경합니다.

---

## 1️⃣ 기존 화면 스타일 참고

### 1.1 참고 화면 찾기

- **신규 시**: 유사한 기존 화면(같은 모듈/카테고리 또는 spov010 등)의 스타일을 확인합니다.
- **수정 시**: 변경 대상 화면의 기존 `.vue`·`.scss` 구조를 확인합니다.

```bash
# 예: spov010 또는 해당 모듈/카테고리 내 화면
# src/pages/sy/ds/spov010/
```

**확인할 파일들** (해당 화면 기준):
- ProgressBar/SumGrid `.vue` + `.scss`
- SearchForm `.vue` + `.scss`
- DataTable `.vue` + `.scss`

### 1.2 스타일 적용 전략

#### ⚠️ DO: 기존 화면·디자인 토큰과 일관된 값 사용

```scss
// ✅ CORRECT - 기존 화면·전역 변수와 일관된 값 사용
.progress-container {
  width: 100%;
  padding: 15px 95px 15px 32px;  // ← 참고 화면과 동일 또는 디자인 토큰
  background-color: var(--bg-2);
  border-radius: var(--border-radius-lg);
  display: flex;
  gap: 90px;
  align-items: center;
}
```

#### ⚠️ DON'T: 기존 패턴 없이 임의 값만 사용

```scss
// ❌ WRONG - 참고 없이 임의 값만 사용 (일관성 깨짐)
.progress-container {
  padding: 20px;  // ← 기존 화면과 불일치
  display: flex;
  gap: 100px;     // ← 기존 화면과 불일치
}
```

---

## 2️⃣ CSS 변수 시스템

### 2.1 전역 CSS 변수

전역/공통 스타일은 프로젝트의 `src/styles`(또는 동일 목적 디렉터리) 규칙을 따릅니다.

```scss
// src/styles/_variables.scss (예)
:root {
  // 색상
  --bg-1: #ffffff;
  --bg-2: #f8f9fa;
  --bg-3: #e9ecef;
  
  --text-primary: #212529;
  --text-secondary: #6c757d;
  --text-disabled: #adb5bd;
  
  --primary-color: #0d6efd;
  --primary-50: rgba(13, 110, 253, 0.1);
  --primary-100: rgba(13, 110, 253, 0.2);
  
  --success-color: #198754;
  --warning-color: #ffc107;
  --danger-color: #dc3545;
  
  // 간격
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  
  // 테두리
  --border-radius-sm: 4px;
  --border-radius-md: 6px;
  --border-radius-lg: 8px;
  
  // 그림자
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}
```

### 2.2 CSS 변수 사용

```scss
// ✅ CORRECT - CSS 변수 사용
.sum-grid-container {
  background-color: var(--bg-2);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-md);
}

button:hover {
  background-color: var(--primary-color);
  color: white;
}
```

---

## 3️⃣ 컴포넌트별 스타일링

### 3.1 SearchForm 스타일

```scss
// [screenId]SearchForm.scss (예: pmdp010SearchForm.scss)
.search-form-container {
  width: 100%;
  padding: 20px;
  background-color: var(--bg-1);
  border-radius: var(--border-radius-lg);
  margin-bottom: var(--spacing-md);
  box-shadow: var(--shadow-sm);
  
  // SearchForm 내부 스타일 커스터마이징
  :deep(.search-form-wrapper) {
    .form-group {
      margin-bottom: var(--spacing-md);
      
      label {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: var(--spacing-xs);
      }
    }
    
    // PrimeVue 컴포넌트 커스터마이징
    .p-inputtext,
    .p-dropdown,
    .p-calendar {
      width: 100%;
      
      &:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 0.2rem var(--primary-50);
      }
    }
  }
  
  // 버튼 영역
  :deep(.button-group) {
    display: flex;
    gap: var(--spacing-sm);
    justify-content: flex-end;
    margin-top: var(--spacing-lg);
    
    .p-button {
      min-width: 100px;
      
      &.p-button-primary {
        background-color: var(--primary-color);
        border-color: var(--primary-color);
        
        &:hover {
          background-color: darken(#0d6efd, 10%);
          border-color: darken(#0d6efd, 10%);
        }
      }
    }
  }
}
```

### 3.2 SumGrid 스타일 (기존 화면 패턴)

```scss
// [screenId]SumGrid.scss (예: pmdp010SumGrid.scss)
.sum-grid-container {
  width: 100%;
  padding: 15px 95px 15px 32px;
  background-color: var(--bg-2);
  border-radius: var(--border-radius-lg);
  display: flex;
  gap: 90px;
  align-items: center;
  margin-bottom: var(--spacing-md);
  
  // 전체 건수 버튼
  .total-btn-box {
    flex-shrink: 0;
    
    .total-btn {
      width: 230px;
      height: 80px;
      padding: 10px 24px;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      justify-content: center;
      gap: 4px;
      background-color: var(--bg-1);
      border: 2px solid transparent;
      border-radius: var(--border-radius-md);
      cursor: pointer;
      transition: all 0.2s ease;
      
      .label {
        font-size: 14px;
        color: var(--text-secondary);
        font-weight: 600;
        line-height: 1.2;
      }
      
      .count {
        font-size: 28px;
        color: var(--text-primary);
        font-weight: 700;
        line-height: 1;
      }
      
      // Hover 효과
      &:hover {
        background-color: var(--primary-color);
        border-color: var(--primary-color);
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        
        .label,
        .count {
          color: white;
        }
      }
      
      // Active 효과
      &:active {
        transform: translateY(0);
        box-shadow: var(--shadow-sm);
      }
      
      // 선택된 상태
      &.active {
        background-color: var(--primary-color);
        border-color: var(--primary-color);
        
        .label,
        .count {
          color: white;
        }
      }
    }
  }
  
  // 진행상태별 버튼들
  .progress-items {
    flex: 1;
    display: flex;
    gap: 24px;
    
    .progress-btn {
      flex: 1;
      min-width: 0;
      height: 80px;
      padding: 10px 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
      background-color: var(--bg-1);
      border: 2px solid transparent;
      border-radius: var(--border-radius-md);
      cursor: pointer;
      transition: all 0.2s ease;
      
      .label {
        font-size: 13px;
        color: var(--text-secondary);
        font-weight: 600;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      
      .count {
        font-size: 24px;
        color: var(--text-primary);
        font-weight: 700;
        line-height: 1;
      }
      
      // Hover 효과
      &:hover {
        background-color: var(--primary-50);
        border-color: var(--primary-color);
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        
        .label {
          color: var(--primary-color);
        }
      }
      
      // Active 효과
      &:active {
        transform: translateY(0);
        box-shadow: var(--shadow-sm);
      }
      
      // 선택된 상태
      &.active {
        background-color: var(--primary-color);
        border-color: var(--primary-color);
        
        .label,
        .count {
          color: white;
        }
      }
    }
  }
}
```

### 3.3 DataTable 전역 스타일 (CRITICAL!)

DataTable 공통 스타일은 프로젝트 전역 스타일 위치(예: `src/styles/components/dataTable.scss`)에 정의된 패턴을 따릅니다.

```scss
// src/styles/components/dataTable.scss (또는 프로젝트 규칙에 맞는 경로)

.p-datatable {
  // 헤더 스타일
  .p-datatable-thead {
    background-color: var(--bg-2);
    
    > tr > th {
      padding: 12px;
      font-weight: 600;
      color: var(--text-primary);
      border-bottom: 2px solid var(--primary-color);
      
      // ⭐ 중앙 정렬 (기본값)
      .p-datatable-column-header-content {
        justify-content: center;
      }
      
      // 좌측 정렬
      &.left .p-datatable-column-header-content {
        justify-content: flex-start;
      }
      
      // 우측 정렬
      &.right .p-datatable-column-header-content {
        justify-content: flex-end;
      }
      
      // ⭐ CSS Containment
      contain: layout style;
    }
  }
  
  // 바디 스타일
  .p-datatable-tbody {
    > tr {
      // ⭐ GPU 가속
      will-change: background-color;
      transition: background-color 0.2s ease;
      
      > td {
        padding: 12px;
        color: var(--text-primary);
        
        // ⭐ CSS Containment
        contain: layout style;
        
        // 중앙 정렬
        &.center {
          text-align: center;
        }
        
        // 우측 정렬
        &.right {
          text-align: right;
        }
      }
      
      // ⭐ Hover 효과 (선택된 행 제외)
      &:hover:not(.p-datatable-row-selected) {
        background-color: var(--primary-50);
      }
      
      // 선택된 행
      &.p-datatable-row-selected {
        background-color: var(--primary-100);
      }
    }
  }
  
  // 스크롤바 스타일
  .p-datatable-scrollable-body {
    &::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    
    &::-webkit-scrollbar-track {
      background-color: var(--bg-2);
      border-radius: 4px;
    }
    
    &::-webkit-scrollbar-thumb {
      background-color: var(--text-disabled);
      border-radius: 4px;
      
      &:hover {
        background-color: var(--text-secondary);
      }
    }
  }
}
```

---

## 4️⃣ 반응형 레이아웃

### 4.1 브레이크포인트

```scss
// _breakpoints.scss
$breakpoint-mobile: 768px;
$breakpoint-tablet: 1024px;
$breakpoint-desktop: 1280px;
$breakpoint-wide: 1920px;

@mixin mobile {
  @media (max-width: #{$breakpoint-mobile - 1px}) {
    @content;
  }
}

@mixin tablet {
  @media (min-width: $breakpoint-mobile) and (max-width: #{$breakpoint-tablet - 1px}) {
    @content;
  }
}

@mixin desktop {
  @media (min-width: $breakpoint-tablet) {
    @content;
  }
}
```

### 4.2 반응형 적용

```scss
.sum-grid-container {
  display: flex;
  gap: 90px;
  
  @include mobile {
    flex-direction: column;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    
    .total-btn-box .total-btn {
      width: 100%;
    }
    
    .progress-items {
      flex-direction: column;
      
      .progress-btn {
        width: 100%;
      }
    }
  }
  
  @include tablet {
    gap: var(--spacing-lg);
    padding: var(--spacing-md) var(--spacing-lg);
    
    .progress-items {
      gap: var(--spacing-md);
    }
  }
}
```

---

## 5️⃣ 애니메이션

### 5.1 Transition

```scss
.progress-btn {
  // ⭐ 여러 속성을 한 번에
  transition: all 0.2s ease;
  
  // ⭐ 개별 속성 제어 (더 좋음)
  transition-property: background-color, border-color, transform, box-shadow;
  transition-duration: 0.2s;
  transition-timing-function: ease;
}
```

### 5.2 Transform

```scss
.progress-btn {
  &:hover {
    // ⭐ GPU 가속 (transform 사용)
    transform: translateY(-2px);
  }
  
  &:active {
    transform: translateY(0);
  }
}
```

### 5.3 Keyframe Animation

```scss
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.datatable-container {
  animation: fadeIn 0.3s ease;
}
```

---

## 6️⃣ :deep() 사용 (Vue 3)

### 6.1 Scoped 스타일 뚫기

```vue
<style scoped lang="scss">
.search-form-container {
  // ⚠️ scoped 때문에 PrimeVue 컴포넌트 스타일 적용 안됨
  .p-inputtext {
    width: 100%;  // ← 적용 안됨
  }
  
  // ✅ :deep()로 해결
  :deep(.p-inputtext) {
    width: 100%;  // ← 적용됨
  }
}
</style>
```

### 6.2 자주 사용하는 패턴

```scss
.my-component {
  // PrimeVue Button
  :deep(.p-button) {
    min-width: 100px;
    
    &.p-button-primary {
      background-color: var(--primary-color);
    }
  }
  
  // PrimeVue InputText
  :deep(.p-inputtext) {
    &:focus {
      border-color: var(--primary-color);
    }
  }
  
  // PrimeVue DataTable
  :deep(.p-datatable) {
    .p-datatable-thead > tr > th {
      background-color: var(--bg-2);
    }
  }
}
```

---

## 7️⃣ SCSS 믹스인

### 7.1 자주 사용하는 믹스인

```scss
// _mixins.scss

// Flexbox 중앙 정렬
@mixin flex-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

// Flexbox 세로 중앙 정렬
@mixin flex-center-vertical {
  display: flex;
  align-items: center;
}

// 말줄임표
@mixin text-ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

// 카드 스타일
@mixin card {
  background-color: var(--bg-1);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-lg);
}

// 버튼 호버 효과
@mixin button-hover {
  transition: all 0.2s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
  
  &:active {
    transform: translateY(0);
    box-shadow: var(--shadow-sm);
  }
}
```

### 7.2 믹스인 사용

```scss
@import '@/styles/mixins';

.total-btn {
  @include card;
  @include button-hover;
  
  .label {
    @include text-ellipsis;
  }
}
```

---

## 8️⃣ 다크 모드 지원 (선택)

### 8.1 CSS 변수 오버라이드

```scss
:root {
  --bg-1: #ffffff;
  --bg-2: #f8f9fa;
  --text-primary: #212529;
}

[data-theme="dark"] {
  --bg-1: #1e1e1e;
  --bg-2: #2d2d2d;
  --text-primary: #f8f9fa;
}
```

### 8.2 테마 전환

```typescript
// stores/theme.ts
export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(false);
  
  const toggleTheme = () => {
    isDark.value = !isDark.value;
    document.documentElement.setAttribute(
      'data-theme',
      isDark.value ? 'dark' : 'light'
    );
  };
  
  return { isDark, toggleTheme };
});
```

---

## ✅ 스타일링 체크리스트

### 기존 화면과 스타일 일관성
- [ ] 참고 화면 확인 (신규 시: spov010 등 / 수정 시: 해당 화면)
- [ ] padding·gap·색상은 디자인 토큰·기존 화면과 맞추기
- [ ] 색상은 CSS 변수 사용
- [ ] hover/active 효과는 기존 패턴 따르기

### DataTable 스타일
- [ ] will-change 추가 (tr)
- [ ] contain 추가 (td, th)
- [ ] hover 선택자 최적화
- [ ] 헤더 중앙 정렬
- [ ] 스크롤바 커스터마이징

### 반응형
- [ ] 모바일 레이아웃 확인
- [ ] 태블릿 레이아웃 확인
- [ ] 데스크탑 레이아웃 확인

### 애니메이션
- [ ] transition 적용
- [ ] transform 사용 (GPU 가속)
- [ ] 부드러운 효과 확인

---

## 🎯 다음 단계

CSS 스타일링이 완료되었다면 **[08_상태관리_패턴.md](./08_상태관리_패턴.md)**로 이동하세요. 신규/수정 모두 상태 관리 패턴을 적용할 때 참고합니다.
