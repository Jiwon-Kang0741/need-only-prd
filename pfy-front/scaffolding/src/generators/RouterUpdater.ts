import { Project, SyntaxKind } from 'ts-morph';
import path from 'path';

/**
 * ts-morph AST 기반 라우터 업데이터.
 * staticRoutes.ts 파일을 파싱하여 생성된 페이지의 라우트를 삽입/삭제.
 *
 * 문자열 replace 대신 AST 를 직접 조작하므로 기존 포맷과 주석이 보존됨.
 */
export class RouterUpdater {
  private project: Project;

  constructor(private readonly routerFilePath: string) {
    this.project = new Project({
      tsConfigFilePath: path.join(path.dirname(routerFilePath), '../../tsconfig.app.json'),
      skipFileDependencyResolution: true,
    });
  }

  /**
   * staticRoutes 배열에 생성된 페이지 라우트를 삽입.
   * - NotFound(/:pathMatch(.*)*) 라우트 직전에 삽입
   * - 동일 name 의 라우트가 이미 존재하면 skip
   */
  addRoute(screenId: string): void {
    const routeId   = screenId.toUpperCase();
    const sourceFile = this.getSourceFile();

    // staticRoutes 변수 초기화(ArrayLiteralExpression) 찾기
    const arrayLiteral = this.getRoutesArray(sourceFile);
    if (!arrayLiteral) {
      throw new Error(`staticRoutes 배열을 찾을 수 없습니다: ${this.routerFilePath}`);
    }

    // 중복 체크
    const fullText = arrayLiteral.getText();
    if (fullText.includes(`'${routeId}'`) || fullText.includes(`"${routeId}"`)) {
      console.log(`[RouterUpdater] route '${routeId}' already exists — skip.`);
      return;
    }

    // NotFound 라우트 인덱스 찾기 (catch-all 패턴)
    const elements   = arrayLiteral.getElements();
    let insertIndex  = elements.length; // 배열 끝

    for (let i = 0; i < elements.length; i++) {
      const text = elements[i].getText();
      if (text.includes('pathMatch') || text.includes('NotFound')) {
        insertIndex = i;
        break;
      }
    }

    const routeCode = this.buildRouteCode(screenId);
    arrayLiteral.insertElement(insertIndex, routeCode);

    sourceFile.saveSync();
    console.log(`[RouterUpdater] route '${routeId}' added at index ${insertIndex}.`);
  }

  /**
   * staticRoutes 배열에서 생성된 페이지 라우트를 제거.
   */
  removeRoute(screenId: string): boolean {
    const routeId    = screenId.toUpperCase();
    const sourceFile = this.getSourceFile();
    const arrayLiteral = this.getRoutesArray(sourceFile);

    if (!arrayLiteral) return false;

    const elements = arrayLiteral.getElements();
    for (let i = 0; i < elements.length; i++) {
      const text = elements[i].getText();
      if (text.includes(`'${routeId}'`) || text.includes(`"${routeId}"`)) {
        arrayLiteral.removeElement(i);
        sourceFile.saveSync();
        console.log(`[RouterUpdater] route '${routeId}' removed.`);
        return true;
      }
    }

    console.log(`[RouterUpdater] route '${routeId}' not found.`);
    return false;
  }

  /** 현재 생성된 라우트 목록 반환 (generated: true 메타 기준) */
  listGeneratedRoutes(): string[] {
    const sourceFile = this.getSourceFile();
    const arrayLiteral = this.getRoutesArray(sourceFile);
    if (!arrayLiteral) return [];

    const result: string[] = [];
    for (const el of arrayLiteral.getElements()) {
      if (el.getText().includes('generated: true')) {
        // name 값 추출
        const match = el.getText().match(/name:\s*['"]([^'"]+)['"]/);
        if (match) result.push(match[1]);
      }
    }
    return result;
  }

  // ── Private Helpers ─────────────────────────────────────────────────────

  private getSourceFile() {
    // 이미 추가됐으면 reload, 아니면 추가
    const existing = this.project.getSourceFile(this.routerFilePath);
    if (existing) {
      existing.refreshFromFileSystemSync();
      return existing;
    }
    return this.project.addSourceFileAtPath(this.routerFilePath);
  }

  private getRoutesArray(sourceFile: ReturnType<Project['addSourceFileAtPath']>) {
    const varDecl = sourceFile.getVariableDeclaration('staticRoutes');
    if (!varDecl) return null;

    return varDecl.getInitializerIfKind(SyntaxKind.ArrayLiteralExpression) ?? null;
  }

  private buildRouteCode(screenId: string): string {
    const routeId  = screenId.toUpperCase();
    const pagePath = `@/pages/generated/${screenId.toLowerCase()}/index.vue`;
    // ts-morph 가 배열 안에 삽입할 때 자체 들여쓰기를 추가하므로
    // 내부 줄은 2칸만 들여쓴다 (전체는 4칸이 됨)
    return `{\n  path: '/${routeId}',\n  name: '${routeId}',\n  meta: { menuId: '${routeId}', generated: true },\n  component: () => import('${pagePath}'),\n}`;
  }
}
