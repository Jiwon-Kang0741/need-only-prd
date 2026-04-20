import path from 'path';
import dotenv from 'dotenv';

// 루트 .env 우선, 없으면 scaffolding/.env (override 없이 fallback)
// need-only-prd 통합: 모든 LLM 설정은 프로젝트 루트 .env에서 관리한다.
//   __dirname = pfy-front/scaffolding/src → 루트는 4레벨 위
const ROOT_ENV = path.join(__dirname, '..', '..', '..', '.env');
const LOCAL_ENV = path.join(__dirname, '..', '.env');
dotenv.config({ path: ROOT_ENV });
dotenv.config({ path: LOCAL_ENV });  // 기존 로컬 env는 fallback 용도

import express from 'express';
import cors from 'cors';

import scaffoldRouter from './routes/scaffold';
import generateRouter from './routes/generate';
import aiGenerateRouter from './routes/ai-generate';
import aiInterviewRouter from './routes/ai-interview-questions';
import aiAnnotateRouter from './routes/ai-annotate';
import interviewResultRouter from './routes/interview-result';
import annotateConstraintsRouter from './routes/annotate-constraints';
import { PATHS } from './utils/paths';

const app  = express();
const PORT = process.env.PORT ? Number(process.env.PORT) : 4000;

// ── Middleware ──────────────────────────────────────────────────────────────
app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

// ── Static UI (public/) ─────────────────────────────────────────────────────
app.use(express.static(PATHS.publicDir));

// ── API Routes ───────────────────────────────────────────────────────────────
app.use('/api/scaffold', scaffoldRouter);
app.use('/api/generate', generateRouter);
app.use('/api/ai-generate', aiGenerateRouter);
app.use('/api/ai-interview-questions', aiInterviewRouter);
app.use('/api/ai-annotate', aiAnnotateRouter);
app.use('/api/generate-interview-result', interviewResultRouter);
app.use('/api/annotate-constraints',     annotateConstraintsRouter);

// ── Health Check ─────────────────────────────────────────────────────────────
app.get('/api/health', (_req, res) => {
  res.json({
    status:      'ok',
    server:      'pfy-scaffolding',
    projectRoot: PATHS.projectRoot,
    timestamp:   new Date().toISOString(),
  });
});

// ── SPA Fallback → index.html ────────────────────────────────────────────────
app.get('*', (_req, res) => {
  res.sendFile(path.join(PATHS.publicDir, 'index.html'));
});

// ── Start ─────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log('');
  console.log('╔══════════════════════════════════════════════════╗');
  console.log('║       pfy-front  Scaffolding Server              ║');
  console.log('╠══════════════════════════════════════════════════╣');
  console.log(`║  UI     →  http://localhost:${PORT}                  ║`);
  console.log(`║  API    →  http://localhost:${PORT}/api/scaffold      ║`);
  console.log(`║  Health →  http://localhost:${PORT}/api/health        ║`);
  console.log('╚══════════════════════════════════════════════════╝');
  console.log('');
  console.log(`  project root : ${PATHS.projectRoot}`);
  console.log(`  pages dir    : ${PATHS.pagesGenerated}`);
  console.log(`  router file  : ${PATHS.staticRoutes}`);
  console.log('');
});

export default app;
