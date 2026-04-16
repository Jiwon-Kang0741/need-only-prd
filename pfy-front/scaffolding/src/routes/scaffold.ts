import { Router, Request, Response } from 'express';
import express from 'express';
import fs from 'fs';
import path from 'path';

import type { ScaffoldRequest, ScaffoldResult, GeneratedPageInfo } from '../types';
import { generateVuePage } from '../generators/VuePageGenerator';
import { RouterUpdater } from '../generators/RouterUpdater';
import {
  PATHS,
  getGeneratedPageDir,
  getGeneratedPageFile,
  getMetaFile,
  ensureDir,
} from '../utils/paths';

const router: Router = express.Router();

// ─────────────────────────────────────────────────────────────────────────────
//  POST /api/scaffold
//  화면 스펙을 받아 Vue 파일을 생성하고 라우터에 등록
// ─────────────────────────────────────────────────────────────────────────────
router.post('/', (req: Request, res: Response) => {
  const body = req.body as ScaffoldRequest;

  // ── 입력 검증 ──────────────────────────────────────────────────────────────
  if (!body.screenId || !body.screenName || !body.pageType) {
    return res.status(400).json({
      success: false,
      message: 'screenId, screenName, pageType 은 필수 항목입니다.',
    } satisfies ScaffoldResult);
  }

  // screenId 는 영문 + 숫자만 허용 (경로 인젝션 방지)
  if (!/^[A-Za-z0-9_]+$/.test(body.screenId)) {
    return res.status(400).json({
      success: false,
      message: 'screenId 는 영문·숫자·언더스코어만 허용됩니다.',
    } satisfies ScaffoldResult);
  }

  try {
    // ── Vue 파일 생성 ────────────────────────────────────────────────────────
    const vueCode  = generateVuePage(body);
    const pageDir  = getGeneratedPageDir(body.screenId);
    const pageFile = getGeneratedPageFile(body.screenId);

    ensureDir(pageDir);
    fs.writeFileSync(pageFile, vueCode, 'utf-8');

    // ── 메타데이터 저장 ──────────────────────────────────────────────────────
    const meta: GeneratedPageInfo = {
      screenId:    body.screenId.toUpperCase(),
      screenName:  body.screenName,
      pageType:    body.pageType,
      routePath:   `/${body.screenId.toUpperCase()}`,
      generatedAt: new Date().toISOString(),
    };
    fs.writeFileSync(getMetaFile(body.screenId), JSON.stringify(meta, null, 2), 'utf-8');

    // ── 라우터 AST 업데이트 ──────────────────────────────────────────────────
    const updater = new RouterUpdater(PATHS.staticRoutes);
    updater.addRoute(body.screenId);

    const result: ScaffoldResult = {
      success:   true,
      message:   `✅ ${body.screenName} (${body.screenId.toUpperCase()}) 생성 완료`,
      filePath:  pageFile,
      routePath: meta.routePath,
      preview:   vueCode,
    };

    console.log(`[scaffold] generated: ${pageFile}`);
    return res.status(201).json(result);
  } catch (err) {
    console.error('[scaffold] error:', err);
    return res.status(500).json({
      success: false,
      message: `생성 중 오류가 발생했습니다: ${(err as Error).message}`,
    } satisfies ScaffoldResult);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
//  GET /api/scaffold
//  생성된 페이지 목록 반환
// ─────────────────────────────────────────────────────────────────────────────
router.get('/', (_req: Request, res: Response) => {
  try {
    ensureDir(PATHS.pagesGenerated);
    const dirs = fs
      .readdirSync(PATHS.pagesGenerated, { withFileTypes: true })
      .filter(d => d.isDirectory());

    const pages: GeneratedPageInfo[] = [];
    for (const dir of dirs) {
      const metaPath = path.join(PATHS.pagesGenerated, dir.name, 'scaffold-meta.json');
      if (fs.existsSync(metaPath)) {
        const raw = fs.readFileSync(metaPath, 'utf-8');
        pages.push(JSON.parse(raw) as GeneratedPageInfo);
      }
    }

    return res.json({ success: true, pages });
  } catch (err) {
    return res.status(500).json({ success: false, message: (err as Error).message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
//  GET /api/scaffold/:screenId/preview
//  생성된 파일 코드 미리보기
// ─────────────────────────────────────────────────────────────────────────────
router.get('/:screenId/preview', (req: Request, res: Response) => {
  const { screenId } = req.params;
  const pageFile     = getGeneratedPageFile(screenId);

  if (!fs.existsSync(pageFile)) {
    return res.status(404).json({ success: false, message: `${screenId} 페이지를 찾을 수 없습니다.` });
  }

  const code = fs.readFileSync(pageFile, 'utf-8');
  return res.json({ success: true, code });
});

// ─────────────────────────────────────────────────────────────────────────────
//  DELETE /api/scaffold/:screenId
//  생성된 페이지 파일 삭제 + 라우터에서 제거
// ─────────────────────────────────────────────────────────────────────────────
router.delete('/:screenId', (req: Request, res: Response) => {
  const { screenId } = req.params;

  try {
    // 파일 시스템 정리
    const pageDir = getGeneratedPageDir(screenId);
    if (fs.existsSync(pageDir)) {
      fs.rmSync(pageDir, { recursive: true, force: true });
    }

    // 라우터에서 제거
    const updater = new RouterUpdater(PATHS.staticRoutes);
    updater.removeRoute(screenId);

    return res.json({
      success: true,
      message: `${screenId.toUpperCase()} 페이지가 삭제되었습니다.`,
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      message: (err as Error).message,
    });
  }
});

export default router;
