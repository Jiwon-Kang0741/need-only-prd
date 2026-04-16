import path from 'path';
import fs from 'fs';

/**
 * 스캐폴딩 서버 기준의 절대 경로 상수들.
 * 이 파일은 scaffolding/src/utils/ 에 위치하므로,
 * 세 단계 위가 pfy-front 프로젝트 루트.
 */
const PROJECT_ROOT = path.resolve(__dirname, '../../..');

export const PATHS = {
  projectRoot:    PROJECT_ROOT,
  srcDir:         path.join(PROJECT_ROOT, 'src'),
  pagesGenerated: path.join(PROJECT_ROOT, 'src', 'pages', 'generated'),
  staticRoutes:   path.join(PROJECT_ROOT, 'src', 'router', 'staticRoutes.ts'),
  publicDir:      path.join(__dirname, '../../public'),
} as const;

/** 생성된 페이지의 디렉터리 경로 반환 */
export function getGeneratedPageDir(screenId: string): string {
  return path.join(PATHS.pagesGenerated, screenId.toLowerCase());
}

/** 생성된 페이지의 index.vue 절대 경로 반환 */
export function getGeneratedPageFile(screenId: string): string {
  return path.join(getGeneratedPageDir(screenId), 'index.vue');
}

/** 메타데이터 JSON 파일 경로 반환 */
export function getMetaFile(screenId: string): string {
  return path.join(getGeneratedPageDir(screenId), 'scaffold-meta.json');
}

/** 디렉터리가 없으면 재귀 생성 */
export function ensureDir(dirPath: string): void {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}
